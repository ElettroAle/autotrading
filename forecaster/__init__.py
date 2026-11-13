"""The forecaster service: price forecasts with Prophet, in its own container (docs/architecture.md §10, ADR 0107).

It sits outside the hexagon, like the tools of the pipeline: the worker reaches it through the adapter
`adapters/outbound/forecaster`, and nothing of `autotrading` is imported here.
"""
