# xAI adapter

The xAI adapter runs `grok-4.6` through the xAI Responses API. It exposes only
the six CyberDefender response functions; xAI web search, X search, code
execution, and other server-side tools are not enabled. Every requested action
is submitted to CyberBroker, provider storage is disabled, and final artifacts
are written only after local assessment validation.

Store the credential as `XAI_API_KEY` in the ignored repository-root `.env`:

```env
XAI_API_KEY=
```

Do not store an xAI credential under `GROQ_API_KEY`; provider labels are part of
the experiment's provenance.
