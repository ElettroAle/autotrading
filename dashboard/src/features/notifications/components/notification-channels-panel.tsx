import { useState, type ReactNode } from 'react';
import { Link } from 'react-router';

import { DataTable, type DataTableColumn } from '@/components/ui/data-table';
import { ErrorMessage } from '@/components/ui/error-message';
import { FORM_CONTROL } from '@/components/ui/form/form-field';
import { SelectField } from '@/components/ui/form/select-field';
import { Loading } from '@/components/ui/loading';

import { useChooseNotificationChannel } from '../api/choose-notification-channel';
import {
  CHANNELS,
  useNotificationChannels,
  type EventChannel,
  type NotificationChannel,
  type NotificationChannels,
} from '../api/get-notification-channels';
import { useRemoveFlowChannelException } from '../api/remove-flow-channel-exception';
import { useSetFlowChannelException } from '../api/set-flow-channel-exception';
import { searchOfTab } from '../utils/notification-tabs';

const COMMAND_FAILED = 'Operazione non riuscita';
// The choice that takes the exception away: the flow follows the general choice again.
const AS_GENERAL = '';
const AS_GENERAL_LABEL = 'come la scelta generale';

type ChannelCellProps = {
  readonly event: string;
  readonly value: string;
  readonly onChoose: (value: string) => void;
  readonly withGeneral?: boolean;
};

// A native drop-down inside the row, with the look of every field: the header of the column names it for the eye,
// the label for readers (ADR scelta-dei-canali-nella-dashboard).
const ChannelCell = ({ event, value, onChoose, withGeneral = false }: ChannelCellProps) => (
  <select
    aria-label={`Canale di ${event}`}
    className={FORM_CONTROL}
    value={value}
    onChange={(change) => onChoose(change.target.value)}
  >
    {withGeneral && <option value={AS_GENERAL}>{AS_GENERAL_LABEL}</option>}
    {CHANNELS.map((channel) => (
      <option key={channel} value={channel}>
        {channel}
      </option>
    ))}
  </select>
);

const Warnings = ({ warnings }: { readonly warnings: readonly string[] }) =>
  warnings.length === 0 ? null : <span className="text-amber-800">{warnings.join(', ')}</span>;

// The reminder where the choice is made: a channel that cannot be reached is configured in the tab of the channels
// (tech-dashboard.md, §Pagine di impostazioni).
const ChannelsToConfigure = ({ warnings }: { readonly warnings: readonly string[] }) =>
  warnings.length === 0 ? null : (
    <p role="status" aria-label="Canali da configurare" className="text-amber-800">
      Canali da configurare: {warnings.join(', ')}.{' '}
      <Link
        to={{ search: searchOfTab('channels') }}
        className="font-medium text-blue-700 underline"
      >
        Configura
      </Link>
    </p>
  );

const isChannel = (value: string): value is NotificationChannel =>
  CHANNELS.some((channel) => channel === value);

const columnsOf = (
  channelCell: (row: EventChannel) => ReactNode,
): DataTableColumn<EventChannel>[] => [
  { header: 'Tipo di evento', cell: (row) => row.event },
  { header: 'Canale', cell: channelCell },
  { header: 'Avviso', cell: (row) => <Warnings warnings={row.warnings} /> },
];

const GeneralChannels = ({ events }: { readonly events: readonly EventChannel[] }) => {
  const choose = useChooseNotificationChannel();
  const columns = columnsOf((row) => (
    <ChannelCell
      event={row.event}
      value={row.channel}
      onChoose={(channel) => {
        if (isChannel(channel)) {
          choose.mutate({ event: row.event, channel });
        }
      }}
    />
  ));
  return (
    <>
      <DataTable
        label="Canali per tipo di evento"
        columns={columns}
        rows={events}
        rowKey={(row) => row.event}
      />
      {choose.isError && <ErrorMessage error={choose.error} prefix={COMMAND_FAILED} />}
    </>
  );
};

type FlowExceptionsProps = {
  readonly flow: NotificationChannels['flows'][number];
  readonly events: readonly EventChannel[];
};

// Every type of event of the flow: its exception, or none when it follows the general choice; the events of the
// account are not there, as they follow the general choice only (R3.5.3).
const FlowExceptions = ({ flow, events }: FlowExceptionsProps) => {
  const except = useSetFlowChannelException();
  const remove = useRemoveFlowChannelException();
  const rows = events
    .filter((event) => event.of_flow)
    .map(
      (event) =>
        flow.exceptions.find((exception) => exception.event === event.event) ?? {
          ...event,
          warnings: [],
        },
    );
  const excepted = new Set(flow.exceptions.map((exception) => exception.event));
  const columns = columnsOf((row) => (
    <ChannelCell
      event={row.event}
      value={excepted.has(row.event) ? row.channel : AS_GENERAL}
      withGeneral
      onChoose={(channel) => {
        if (isChannel(channel)) {
          except.mutate({ flowId: flow.flow_id, event: row.event, channel });
          return;
        }
        remove.mutate({ flowId: flow.flow_id, event: row.event });
      }}
    />
  ));
  const failed = except.error ?? remove.error;
  return (
    <>
      <DataTable
        label={`Eccezioni di ${flow.name}`}
        columns={columns}
        rows={rows}
        rowKey={(row) => row.event}
      />
      {failed !== null && <ErrorMessage error={failed} prefix={COMMAND_FAILED} />}
    </>
  );
};

const Exceptions = ({ channels }: { readonly channels: NotificationChannels }) => {
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
      {flow !== undefined && <FlowExceptions flow={flow} events={channels.events} />}
    </div>
  );
};

/**
 * The channel of every type of event, for all the flows, and the exceptions of one flow, with the warning of a chosen
 * channel that is not linked; the bell of the dashboard is not chosen here, it receives every notification (R3.5.3).
 */
export const NotificationChannelsPanel = () => {
  const channels = useNotificationChannels();
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
          <ChannelsToConfigure warnings={channels.data.warnings} />
          <GeneralChannels events={channels.data.events} />
          <Exceptions channels={channels.data} />
        </>
      )}
    </section>
  );
};
