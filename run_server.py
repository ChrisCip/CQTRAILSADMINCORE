import uvicorn

if __name__ == "__main__":
    print("⚡ Iniciando CQ Trails Admin API")
    print("📄 Documentación Swagger UI: http://127.0.0.1:8000/docs")
    print("📖 Documentación ReDoc: http://127.0.0.1:8000/redoc")
    print("🔎 API Status: http://127.0.0.1:8000/")
    print("🔄 Presione CTRL+C para detener el servidor")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
