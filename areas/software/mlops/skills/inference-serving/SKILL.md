---
name: inference-serving
description: "Provides a FastAPI inference endpoint pattern and a latency checklist for model serving; use when deploying a model to an API endpoint or optimizing inference latency."
---

# Skill: Inference Serving

## When to load

When deploying a model to an API endpoint or optimizing inference latency.

## FastAPI Inference Endpoint

```python
@app.on_event("startup")
def load_model():
    app.state.model = mlflow.pyfunc.load_model("models:/churn-predictor/Production")
    app.state.preprocessor = load_preprocessor()

@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest):
    try:
        features = app.state.preprocessor.transform([request.features])
        probability = app.state.model.predict(features)[0]
        log_prediction(request.user_id, request.features, float(probability))
        return PredictionResponse(
            user_id=request.user_id,
            churn_probability=float(probability),
        )
    except Exception as e:
        logger.error("Inference failed", error=str(e))
        return PredictionResponse(user_id=request.user_id, churn_probability=FALLBACK_PROBABILITY)
```

## Latency Checklist

- [ ] Model loaded at startup, not per request
- [ ] Input preprocessing vectorized (batch)
- [ ] ONNX conversion for framework-agnostic optimization
- [ ] Batch inference enabled for high-throughput
