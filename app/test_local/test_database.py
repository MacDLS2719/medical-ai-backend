from sqlalchemy import text

from app.core.database import engine


try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        print("=================================")
        print("Conexion a PostgreSQL exitosa")
        print("Resultado:", result.scalar())
        print("=================================")

except Exception as e:
    print("=================================")
    print("Error conectando a PostgreSQL")
    print(e)
    print("=================================")