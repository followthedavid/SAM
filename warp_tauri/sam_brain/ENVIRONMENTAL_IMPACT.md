# Environmental Impact: Claude vs Local LLM

## Honest Assessment

This document provides transparent, research-based estimates of the environmental cost of LLM usage. Numbers are approximations based on available research.

---

## Cloud LLM (Claude API) Costs

### Energy per Request
| Request Type | Tokens | Energy (Wh) | CO2 (grams) |
|-------------|--------|-------------|-------------|
| Simple query | ~500 | 0.5-2 | 0.2-1.0 |
| Code generation | ~2000 | 2-8 | 1-4 |
| Complex reasoning | ~5000 | 5-20 | 2.5-10 |
| Extended thinking | ~10000+ | 10-50 | 5-25 |

**Sources:**
- Strubell et al. (2019): "Energy and Policy Considerations for Deep Learning"
- Patterson et al. (2021): "Carbon Emissions and Large Neural Network Training"
- Luccioni et al. (2023): "Estimating the Carbon Footprint of BLOOM"

### Water Usage
Data centers use water for cooling. Estimates:
- **~0.5-1 mL water per 1000 tokens** (depending on datacenter efficiency)
- A typical Claude conversation (~5000 tokens): **2.5-5 mL water**

**Source:** Li et al. (2023): "Making AI Less Thirsty"

### Monthly Impact (Moderate User)
Assuming 50 Claude conversations/day, 2000 tokens average:
- **Energy:** 50-200 kWh/month
- **CO2:** 25-100 kg/month (depends on grid)
- **Water:** 5-10 liters/month

---

## Local LLM (SAM on Mac Mini M2) Costs

### Energy per Request
| Request Type | Tokens | Energy (Wh) | CO2 (grams) |
|-------------|--------|-------------|-------------|
| Simple query | ~500 | 0.05-0.1 | 0.02-0.05 |
| Code assist | ~2000 | 0.1-0.3 | 0.05-0.15 |
| Complex task | ~5000 | 0.2-0.5 | 0.1-0.25 |

**Why so much lower?**
- Apple Silicon is extremely power efficient (5-15W vs 300-700W for datacenter GPUs)
- No datacenter overhead (cooling, networking, redundancy)
- Model is smaller (1-8B vs 175B+ parameters)

### Water Usage
- **0 mL** - Mac Mini uses passive/fan cooling, no water

### Monthly Impact (Same Usage)
50 local queries/day:
- **Energy:** 1-5 kWh/month
- **CO2:** 0.5-2.5 kg/month
- **Water:** 0 liters

---

## Comparison: SAM vs Pure Claude

| Metric | Pure Claude | SAM (70% Local) | Savings |
|--------|-------------|-----------------|---------|
| Energy/month | 50-200 kWh | 15-65 kWh | **70%** |
| CO2/month | 25-100 kg | 8-33 kg | **70%** |
| Water/month | 5-10 L | 1.5-3 L | **70%** |
| Cost/month | $50-200* | $15-65* | **70%** |

*Assuming Claude Pro subscription + API usage

---

## Real-World Context

### What does 1 kWh power?
- 30 hours of LED lighting
- 1 load of laundry
- 10 smartphone charges
- 1 hour of air conditioning

### What does 1 liter of water equal?
- 2 standard water bottles
- 1/50th of a shower
- 1/200th of a bath

### Your Annual Impact (SAM vs Claude)

| Scenario | Energy | CO2 | Water | Trees to Offset |
|----------|--------|-----|-------|-----------------|
| Pure Claude | 600-2400 kWh | 300-1200 kg | 60-120 L | 15-60 trees |
| SAM (70% local) | 180-720 kWh | 90-360 kg | 18-36 L | 4-18 trees |
| **Saved** | **420-1680 kWh** | **210-840 kg** | **42-84 L** | **11-42 trees** |

---

## Caveats & Honesty

### What This Doesn't Account For
1. **Training costs** - Claude's training used massive energy, but that's amortized across all users
2. **Your Mac's total power** - These are marginal costs, not total device power
3. **Network transmission** - Data transfer has energy costs too
4. **Hardware manufacturing** - Your Mac's production had environmental impact

### Uncertainties
- Cloud energy estimates vary by 2-10x depending on datacenter
- Actual token counts vary significantly by task
- Grid carbon intensity varies by region (0.2-0.8 kg CO2/kWh)

### Why Local Isn't Always Better
- If local model gives worse answers → more iterations → more total energy
- Training a custom local model uses significant energy
- Some tasks genuinely need Claude's capability

---

## SAM's Philosophy

**Goal:** Use the right tool for the job.
- Simple tasks → Local (free, green)
- Complex tasks → Claude (worth the cost)
- Learn from Claude → Improve local (long-term savings)

**Not:** Avoid Claude at all costs
**But:** Don't waste Claude on things that don't need it

---

## Display in App

SAM should show:
```
Today's Stats:
  Local queries: 47 (saved ~50 Wh, ~0 mL water)
  Claude queries: 3 (used ~15 Wh, ~8 mL water)

Monthly Estimate:
  Energy saved: ~1.5 kWh
  CO2 avoided: ~0.75 kg
  Water saved: ~2.5 L
```

---

## References

1. Strubell, E., Ganesh, A., & McCallum, A. (2019). Energy and Policy Considerations for Deep Learning in NLP.
2. Patterson, D., et al. (2021). Carbon Emissions and Large Neural Network Training. arXiv:2104.10350.
3. Luccioni, A.S., et al. (2023). Estimating the Carbon Footprint of BLOOM. arXiv:2211.02001.
4. Li, P., et al. (2023). Making AI Less "Thirsty". arXiv:2304.03271.
5. Apple Silicon efficiency data from Apple technical specifications.

---

**Last Updated:** 2026-01-12
**Disclaimer:** All figures are estimates. Actual impact varies by usage patterns, grid mix, and datacenter efficiency.
