import { useId, useState, type ReactNode } from 'react';
import { Link } from 'react-router';

import { DataTable, type DataTableColumn } from '@/components/ui/data-table';
import { ErrorMessage } from '@/components/ui/error-message';
import { FormAlert } from '@/components/ui/form/input-field';
import { SelectField } from '@/components/ui/form/select-field';
import { Icon } from '@/components/ui/icons/icon';
import { Loading } from '@/components/ui/loading';
import { SessionExpiredError } from '@/lib/auth';

import { useChooseNotificationChannel } from '../api/choose-notification-channel';
import {
  useNotificationChannels,
  type ChannelState,
  type EventChannel,
  type NotificationChannel,
  type NotificationChannels,
} from '../api/get-notification-channels';
import { useRemoveFlowChannelException } from '../api/remove-flow-channel-exception';
import { useSetFlowChannelException } from '../api/set-flow-channel-exception';
import { searchOfTab } from '../utils/notification-tabs';

const COMMAND_FAILED = 'Operazione non riuscita';
// The switch that takes the exception away: the flow follows the general choice again.
const AS_GENERAL = 'Come la scelta generale';

const SWITCH =
  'inline-flex items-center gap-1 rounded-full border px-3 py-1 text-sm disabled:cursor-not-allowed disabled:opacity-60';
const SWITCH_ON = 'border-blue-700 bg-blue-700 text-white';
const SWITCH_OFF = 'border-slate-300 bg-white text-slate-700';

/** The reason a command failed, for the alert of the form; an expired session says nothing, as the user is already
 * back at the sign-in. */
const failureOf = (error: Error | null) =>
  error === null || error instanceof SessionExpiredError
    ? undefined
    : { message: `${COMMAND_FAILED}: ${error.message}` };

/** The channels with one turned on or off, in the order the API lists the channels. */
const toggled = (
  channels: readonly ChannelState[],
  chosen: readonly NotificationChannel[],
  channel: NotificationChannel,
): NotificationChannel[] =>
  channels
    .map((state) => state.channel)
    .filter((each) => (each === channel ? !chosen.includes(each) : chosen.includes(each)));

/** The id of the reason a channel is not configured, which its disabled switches point to. */
const reasonIdOf = (reasonsId: string, index: number) => `${reasonsId}-${index}`;

type SwitchProps = {
  readonly label: string;
  readonly on: boolean;
  readonly onPress: () => void;
  readonly disabled?: boolean;
  readonly describedBy?: string;
};

// A button with aria-pressed: its state shows with an icon and the text, never the colour alone.
const Switch = ({ label, on, onPress, disabled = false, describedBy }: SwitchProps) => (
  <button
    type="button"
    aria-pressed={on}
    aria-describedby={describedBy}
    disabled={disabled}
    className={`${SWITCH} ${on ? SWITCH_ON : SWITCH_OFF}`}
    onClick={onPress}
  >
    <Icon name={on ? 'circle-check' : 'plus'} />
    {label}
  </button>
);

type ChannelSwitchesProps = {
  readonly event: string;
  readonly channels: readonly ChannelState[];
  readonly chosen: readonly NotificationChannel[];
  readonly reasonsId: string;
  readonly onChoose: (channels: NotificationChannel[]) => void;
  readonly children?: ReactNode;
};

// One switch per channel the API lists, wrapping when they do not fit: a new channel is one switch more. A channel not
// configured cannot be turned on, and points to the reason with «Configura»; when it is on it can still be turned off
// (ADR interruttori-dei-canali-nelle-preferenze).
const ChannelSwitches = ({
  event,
  channels,
  chosen,
  reasonsId,
  onChoose,
  children,
}: ChannelSwitchesProps) => (
  <div role="group" aria-label={`Canali di ${event}`} className="flex flex-wrap gap-2">
    {children}
    {channels.map((state, index) => {
      const on = chosen.includes(state.channel);
      const unavailable = !state.configured && !on;
      return (
        <Switch
          key={state.channel}
          label={state.channel}
          on={on}
          disabled={unavailable}
          describedBy={unavailable ? reasonIdOf(reasonsId, index) : undefined}
          onPress={() => onChoose(toggled(channels, chosen, state.channel))}
        />
      );
    })}
  </div>
);

// The reminder where the choice is made: a chosen channel that cannot be reached is configured in the tab of the
// channels (tech-dashboard.md, §Pagine di impostazioni).
const ConfigureLink = () => (
  <Link to={{ search: searchOfTab('channels') }} className="font-medium text-blue-700 underline">
    Configura
  </Link>
);

const Warnings = ({ warnings }: { readonly warnings: readonly string[] }) =>
  warnings.length === 0 ? null : (
    <span className="text-amber-800">
      {warnings.join(', ')}. <ConfigureLink />
    </span>
  );

// Every channel not configured with its reason, whatever the choices (R3.5.5), and the way to configure it.
const ChannelsToConfigure = ({ channels, reasonsId }: ChannelsProps) => {
  const missing = channels.channels
    .map((state, index) => ({ state, id: reasonIdOf(reasonsId, index) }))
    .filter(({ state }) => !state.configured);
  return missing.length === 0 ? null : (
    <p role="status" aria-label="Canali da configurare" className="text-amber-800">
      Canali da configurare:{' '}
      {missing.map(({ state, id }, index) => (
        <span key={state.channel}>
          {index > 0 && ', '}
          <span id={id}>{state.warnings.join(', ')}</span>
        </span>
      ))}
      . <ConfigureLink />
    </p>
  );
};

const columnsOf = (switches: (row: EventChannel) => ReactNode): DataTableColumn<EventChannel>[] => [
  { header: 'Tipo di evento', cell: (row) => row.event },
  { header: 'Canali', cell: switches },
  { header: 'Avviso', cell: (row) => <Warnings warnings={row.warnings} /> },
];

type ChannelsProps = {
  readonly channels: NotificationChannels;
  readonly reasonsId: string;
};

const GeneralChannels = ({ channels, reasonsId }: ChannelsProps) => {
  const choose = useChooseNotificationChannel();
  const columns = columnsOf((row) => (
    <ChannelSwitches
      event={row.event}
      channels={channels.channels}
      chosen={row.channels}
      reasonsId={reasonsId}
      onChoose={(chosen) => choose.mutate({ event: row.event, channels: chosen })}
    />
  ));
  return (
    <>
      <DataTable
        label="Canali per tipo di evento"
        columns={columns}
        rows={channels.events}
        rowKey={(row) => row.event}
      />
      <FormAlert error={failureOf(choose.error)} />
    </>
  );
};

type FlowExceptionsProps = ChannelsProps & {
  readonly flow: NotificationChannels['flows'][number];
};

// Every type of event of the flow: its exception, or the general choice it follows; the events of the account are not
// there, as they follow the general choice only (R3.5.3). Turning a channel of an event without exception starts one
// from the general choice.
const FlowExceptions = ({ channels, reasonsId, flow }: FlowExceptionsProps) => {
  const except = useSetFlowChannelException();
  const remove = useRemoveFlowChannelException();
  const excepted = new Map(flow.exceptions.map((exception) => [exception.event, exception]));
  const rows = channels.events
    .filter((event) => event.of_flow)
    .map((event) => excepted.get(event.event) ?? { ...event, warnings: [] });
  const columns = columnsOf((row) => {
    const hasException = excepted.has(row.event);
    return (
      <ChannelSwitches
        event={row.event}
        channels={channels.channels}
        chosen={row.channels}
        reasonsId={reasonsId}
        onChoose={(chosen) =>
          except.mutate({ flowId: flow.flow_id, event: row.event, channels: chosen })
        }
      >
        <Switch
          label={AS_GENERAL}
          on={!hasException}
          onPress={() => {
            if (hasException) {
              remove.mutate({ flowId: flow.flow_id, event: row.event });
            }
          }}
        />
      </ChannelSwitches>
    );
  });
  return (
    <>
      <DataTable
        label={`Eccezioni di ${flow.name}`}
        columns={columns}
        rows={rows}
        rowKey={(row) => row.event}
      />
      <FormAlert error={failureOf(except.error ?? remove.error)} />
    </>
  );
};

const Exceptions = ({ channels, reasonsId }: ChannelsProps) => {
  const [flowId, setFlowId] = useState('');
  const flow = channels.flows.find((candidate) => candidate.flow_id === flowId);
  return (
    <div className="space-y-3">
      <h3 className="font-semibold">Eccezioni di un flusso</h3>
      <SelectField
        label="Flusso"
        placeholder="Scegli un flusso"
        choices={channels.flows.map((each) => ({ value: each.flow_id, label: each.name }))}
        value={flowId}
        onChange={(change) => setFlowId(change.target.value)}
      />
      {flow !== undefined && (
        <FlowExceptions channels={channels} reasonsId={reasonsId} flow={flow} />
      )}
    </div>
  );
};

/**
 * The channels of every type of event, for all the flows, and the exceptions of one flow: a switch per channel of the
 * platform in the row of the event, a card per event on a phone, with the warning of a chosen channel that is not
 * linked; the bell of the dashboard is not chosen here, it receives every notification (R3.5.3, ADR
 * interruttori-dei-canali-nelle-preferenze).
 */
export const NotificationChannelsPanel = () => {
  const channels = useNotificationChannels();
  const reasonsId = useId();
  return (
    <section
      aria-labelledby="notification-channels-title"
      className="space-y-4 rounded border border-slate-200 bg-white p-4"
    >
      <h2 id="notification-channels-title" className="text-xl font-semibold">
        Canali per tipo di evento
      </h2>
      {channels.isPending && <Loading />}
      {channels.isError && <ErrorMessage error={channels.error} />}
      {channels.isSuccess && (
        <>
          <ChannelsToConfigure channels={channels.data} reasonsId={reasonsId} />
          <GeneralChannels channels={channels.data} reasonsId={reasonsId} />
          <Exceptions channels={channels.data} reasonsId={reasonsId} />
        </>
      )}
    </section>
  );
};
