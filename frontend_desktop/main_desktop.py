import sys
from PyQt6.QtWidgets import QApplication
from login_desktop import VentanaLogin
from main_window import VentanaPrincipal

if __name__ == '__main__':
    app = QApplication(sys.argv)

    ventana_login = VentanaLogin()
    ventana_login.show()

    app.exec()

    if ventana_login.token:
        ventana_principal = VentanaPrincipal(ventana_login.token)
        ventana_principal.show()
        sys.exit(app.exec())
    else:
        sys.exit(0)