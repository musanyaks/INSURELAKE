from ingestion.api.mpesa import router as mpesa_router, _register_callback_route

app.include_router(mpesa_router)
_register_callback_route(app, lambda: producer)  # producer is your module-level KafkaProducer