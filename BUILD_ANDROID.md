# Generar el .apk

Buildozer solo corre en Linux (nativo, WSL en Windows, o una VM). No hace falta
tener Android Studio instalado — buildozer baja el SDK/NDK solo la primera vez.

## 1. Instalar buildozer (una vez)

```bash
pip install buildozer cython --break-system-packages
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf \
  libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev \
  libtinfo5 cmake libffi-dev libssl-dev
```

## 2. Ubicar los archivos

Poné `sistema_diario.py` y `buildozer.spec` en la misma carpeta, y renombrá
el script a `main.py` (buildozer busca `main.py` por defecto):

```bash
mkdir sistema_diario_app && cd sistema_diario_app
cp /ruta/a/sistema_diario.py main.py
cp /ruta/a/buildozer.spec .
```

## 3. Editar `package.domain` en `buildozer.spec`

Cambiá `org.tuusuario` por algo tuyo (ej: `com.gonzalo`), así el paquete
Android queda con un id único.

## 4. Compilar

```bash
buildozer -v android debug
```

La primera vez tarda bastante (descarga el SDK/NDK de Android, ~unos GB).
El .apk queda en `bin/sistemadiario-0.1-arm64-v8a-debug.apk`.

## 5. Instalar en el celular

Con el celular conectado por USB y depuración USB activada:

```bash
buildozer android deploy run
```

O simplemente copiá el .apk al celular e instalalo manualmente (vas a
necesitar permitir "instalar apps de fuentes desconocidas" la primera vez).

## Notas

- El permiso `INTERNET` ya está agregado en el spec (lo necesita para
  buscar las cotizaciones del dólar).
- Android puede pausar la actualización en segundo plano si la app no
  está abierta — es normal, al volver a abrirla se actualiza sola.
- Si querés un ícono propio, agregá un `icon.png` (512x512) a la carpeta
  y descomentá la línea `icon.filename` en `buildozer.spec`.
