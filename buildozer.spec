[app]

title = Sistema Diario
package.name = sistemadiario
package.domain = org.tuusuario

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,ttf

version = 0.1

requirements = python3,kivy==2.3.1,requests,certifi,urllib3,charset_normalizer,idna

orientation = portrait
fullscreen = 0

# Icono y splash (opcionales). Descomentar y poner tus propios archivos
# 512x512 (icon) y 720x1280 (splash) en la carpeta del proyecto si querés
# reemplazar los de Kivy por defecto.
# icon.filename = %(source.dir)s/icon.png
# presplash.filename = %(source.dir)s/presplash.png

android.permissions = INTERNET

# API/NDK: dejar que python-for-android use sus valores por defecto suele
# ser lo más estable. Si necesitás fijarlos, descomentá y ajustá:
# android.api = 34
# android.minapi = 21
# android.ndk = 25b

android.archs = arm64-v8a, armeabi-v7a

# Evita que la Doze/optimización de batería mate el refresco de fondo
# de las cotizaciones tan agresivamente (no es 100% garantía, Android
# igual puede pausar la app si no está en primer plano).
# android.wakelock = True

[buildozer]
log_level = 2
warn_on_root = 1
