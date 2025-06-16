# OT-Service-Support-Assistant

## Architecture Decision Records

Whenever we make a significant architectural choice for this OT-Debug Chatbot, we record it here.

### ADR 0001: Choose Streamlit for User Interface  
**Date:** 2025-06-16  
**Status:** Accepted  
```mermaid
graph LR
    A[User Browser] -->|HTTP| B[Streamlit App]
    B -->|POST /ask| C[FastAPI Backend]
    C -->|HTTP| D[Langflow MCP Server]
    subgraph Langflow Flow
      D1[Webhook Input] --> E[Retriever]
      F[Vector Store] <-- G[Document Loader + Splitter + Embeddings]
      E --> H[LLM Chain]
      H --> I[JSON Response]
    end
    G --> F
    H --> F  &nbsp; <!-- for RAG, LLM may re-query embeddings -->
```

#### Context  
We need a lightweight, interactive web UI that allows enterprise users to type in OT system issues and get back suggestions. It should be simple to deploy alongside our backend service.

#### Decision  
Use [Streamlit](https://streamlit.io) for the front end.  

#### Consequences  
- **Pro:** Rapid prototyping, minimal boilerplate, built-in support for chat-style layouts.  
- **Con:** Limited custom component flexibility (but acceptable for v1).  

---

### ADR 0002: Use FastAPI as Backend Bridge  
**Date:** 2025-06-16  
**Status:** Accepted  

#### Context  
We need a RESTful service to receive queries from the UI, read our `mcp.json` config, and forward requests to the Langflow MCP server.

#### Decision  
Implement the backend in Python using [FastAPI](https://fastapi.tiangolo.com).  

#### Consequences  
- **Pro:** Async support, automatic OpenAPI docs, easy integration with `httpx`.  
- **Con:** Adds an extra hop between UI and Langflow (acceptable for decoupling).  

---

### ADR 0003: Use Langflow MCP Server & RAG  
**Date:** 2025-06-16  
**Status:** Accepted  

#### Context  
We have many SOP documents that must be searched and fed to an LLM dynamically. We want to keep document parsing, vector storage, and prompt templating in a single flow.

#### Decision  
Host a “Webhook” flow in Langflow MCP that:
1. Loads & splits SOPs in `./sops/`  
2. Indexes them with FAISS (persisted locally)  
3. Retrieves top-k chunks at query time  
4. Passes them plus user query into an OpenAI LLM chain  

#### Consequences  
- **Pro:** All RAG logic lives in one place, easy to modify prompts or retriever parameters.  
- **Con:** Requires MCP server uptime; introduces dependency on Langflow.  

---

### ADR 0004: Vector Store – FAISS on Disk  
**Date:** 2025-06-16  
**Status:** Accepted  

#### Context  
We need fast similarity search over ~100+ SOP documents.  

#### Decision  
Use FAISS local index persisted under `./.vectorstore`.  

#### Consequences  
- **Pro:** No external DB, low-latency kNN lookups.  
- **Con:** Scaling beyond a few GB may require moving to a hosted vector DB later.  

---

### ADR 0005: OpenAI GPT-4o for LLM  
**Date:** 2025-06-16  
**Status:** Accepted  

#### Context  
We need a powerful model to interpret SOP context and troubleshoot OT-system issues effectively.

#### Decision  
Use `gpt-4o` via OpenAI.  

#### Consequences  
- **Pro:** State-of-the-art reasoning and instruction-following.  
- **Con:** Cost per token; may consider local alternatives in future.  

---

(When a new major decision arises—e.g. switching to Chroma, adding caching middleware, or upgrading the UI framework—append a new ADR with a fresh ID and date.)

