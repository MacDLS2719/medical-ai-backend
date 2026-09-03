import os
import sys

# Add backend directory to sys path
sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

from app.core.database import SessionLocal
from app.models.user import User


# ==========================================================
# DATOS DEL VERIFICADOR
# ==========================================================

EMAIL = "verificador@medical-ai.com"
PASSWORD_HASH = "nopass"


# ==========================================================
# CREAR USUARIO VERIFICADOR
# ==========================================================

def create_verifier():

    db = SessionLocal()

    try:

        print("Creando usuario verificador...")

        # --------------------------------------------------
        # VERIFICAR SI YA EXISTE
        # --------------------------------------------------

        user = (
            db.query(User)
            .filter_by(email=EMAIL)
            .first()
        )

        if user:

            print()
            print("==========================================")
            print("EL USUARIO YA EXISTE")
            print("==========================================")
            print(f"ID: {user.id}")
            print(f"Email: {user.email}")
            print(f"Rol: {user.role}")
            print(f"Activo: {user.is_active}")
            print("==========================================")

            return

        # --------------------------------------------------
        # CREAR USUARIO
        # --------------------------------------------------

        user = User(
            email=EMAIL,
            password_hash=PASSWORD_HASH,
            role="verifier",
            language="es",
            is_active=True,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        print()
        print("==========================================")
        print("USUARIO VERIFICADOR CREADO")
        print("==========================================")
        print(f"ID: {user.id}")
        print(f"Email: {user.email}")
        print(f"Rol: {user.role}")
        print(f"Password hash: {user.password_hash}")
        print(f"Activo: {user.is_active}")
        print("==========================================")

    except Exception as e:

        db.rollback()

        print()
        print("==========================================")
        print("ERROR CREANDO USUARIO VERIFICADOR")
        print("==========================================")
        print(str(e))
        print("==========================================")

    finally:

        db.close()


if __name__ == "__main__":
    create_verifier()

