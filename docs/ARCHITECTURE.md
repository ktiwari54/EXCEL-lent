# Data Analyst Engine — Architecture

```text
                    DATA ANALYST ENGINE
                           │
                    ┌──────▼──────┐
                    │  AI / Intent │
                    └──────┬──────┘
                           │
                 ┌─────────▼─────────┐
                 │ Semantic Data Layer│
                 └─────────┬─────────┘
                           │
              ┌────────────▼────────────┐
              │ Business Intelligence   │
              │        Engine           │
              └────────────┬────────────┘
                           │
       ┌──────────┬────────┼────────┬──────────┐
       ▼          ▼        ▼        ▼          ▼
   Formula     Lookup    Time     Statistics   KPI
    Engine     Engine   Engine     Engine     Engine
       │          │        │          │          │
       └──────────┴────────┴──────────┴──────────┘
                           │
                  ┌────────▼────────┐
                  │ Insight Engine  │
                  └────────┬────────┘
                           │
                  ┌────────▼────────┐
                  │ Result Engine   │
                  └─────────────────┘
```

## Layers

| Layer | Responsibility | Code |
|-------|----------------|------|
| **AI / Intent** | Map natural language → task + config hints | `engines/ai_intent.py` |
| **Semantic Data Layer** | Columns, roles, measures, dimensions, metrics catalog | `engines/semantic.py` |
| **BI Engine** | Orchestrate task request → sub-engines | `engines/bi_engine.py` |
| **Formula Engine** | SUM, AVG, growth, variance, ratios… | `engines/formula_engine.py` |
| **Lookup Engine** | Match / join / reconcile | `engines/lookup_engine.py` |
| **Time Engine** | Periods, MoM, YoY, YTD, grain | `engines/time_engine.py` |
| **Statistics Engine** | Rank, top/n, distribution, outliers | `engines/stats_engine.py` |
| **KPI Engine** | Cards, targets, contribution | `engines/kpi_engine.py` |
| **Insight Engine** | Alerts, narrative findings | `engines/insight_engine.py` |
| **Result Engine** | Normalize tables/charts/KPIs for UI/export | `engines/result_engine.py` |

## Product stages (user journey)

1. **Upload & Profile** → feeds Semantic Data Layer  
2. **Task Selection** → AI / Intent + task registry  
3. **Configure** → Task Request object  
4. **Process** → BI Engine + specialists → Insight → Result  
5. **Present** → UI / Excel export  

## Data flow

```text
User NL / UI
    → AI/Intent (optional)
    → Task Registry + Configure → TaskRequest
    → Semantic model (from dataset profile)
    → BI Engine.dispatch(task_request, semantic, raw_df)
         → Formula | Lookup | Time | Stats | KPI
    → Insight Engine
    → Result Engine → UI
```

## Principle

Excel formulas stay **inside** specialist engines.  
Users interact with tasks and outcomes — not VLOOKUP/SUMIFS.
