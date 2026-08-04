"""
Sistema Diario — versión Kivy
==============================
Puerto de la app original en Flet. Se mantiene el mismo lenguaje visual
(fondo oscuro + acento dorado #D4AF37) pero con detalles tipo Windows 11:
esquinas redondeadas en tarjetas y botones, una "pill" de navegación
inferior y tarjetas con separación tipo "mica".

Requisitos:
    pip install kivy requests

Ejecutar:
    python sistema_diario.py
"""

from datetime import datetime, timedelta
import json
import random
import threading

import requests

from kivy import platform

# El tamaño de ventana de escritorio se define ANTES de importar Window:
# asignar Window.size en caliente después de creada la ventana puede dejar
# el primer frame con el buffer de recorte (stencil) desincronizado.
if platform not in ("android", "ios"):
    from kivy.config import Config
    Config.set("graphics", "width", "410")
    Config.set("graphics", "height", "860")  # simula proporción de celular en escritorio

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.metrics import dp, sp
from kivy.storage.jsonstore import JsonStore
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen, ScreenManager, NoTransition
from kivy.uix.widget import Widget

# ---------------------------------------------------------------- #
# Paleta (misma identidad que la versión Flet)
# ---------------------------------------------------------------- #
BG = (0.07, 0.07, 0.07, 1)
CARD = (0.10, 0.10, 0.10, 1)
CARD_ALT = (0.16, 0.16, 0.16, 1)
GOLD = (0.831, 0.686, 0.216, 1)      # #D4AF37
WHITE = (1, 1, 1, 1)
RED = (0.86, 0.18, 0.18, 1)
YELLOW = (1, 0.85, 0.15, 1)
GREEN = (0.30, 0.75, 0.40, 1)
GREY = (0.55, 0.55, 0.55, 1)
ORANGE = (0.92, 0.58, 0.15, 1)
BLACK = (0, 0, 0, 1)

Window.clearcolor = BG

# ---------------------------------------------------------------- #
# Datos / lógica (idéntica a la original, sin el motor async de Flet)
# ---------------------------------------------------------------- #
FechaHoy = datetime.now()
FechaActual = FechaHoy.strftime("%A %d/%m")
fecha_hoy_llave = FechaHoy.strftime("%Y-%m-%d")

dia = FechaHoy.strftime("%A").lower()

if dia == "sunday":
    D = 0
    Cuerpo = None
elif dia in ("monday", "friday", "wednesday"):
    D = 1
    Cuerpo = "Gimnasio"
else:
    D = 2
    Cuerpo = "Descanso Activo"

materias_colegio = {
    "monday": "1. Ingles // 2. Matematica // 3. Cs Sociales // 4. EI Tecno. || 12:15",
    "tuesday": "1. Ingles // 2. Artes V. // 3. Lengua // 4. Cs Sociales // 5. Form. Crist. || 12:55",
    "wednesday": "1. Lengua // 2. Biología // 3. Artes V. || 11:25",
    "thursday": "1. FVT // 2. Matemática // 3. EI Tecno. || 11:25",
    "friday": "1. EI Tecno. // 2. Biologia // 3. ED. Fisica. || 12:15",
    "saturday": "¡Libre!",
    "sunday": "¡Libre!",
}

dias_es = {
    "monday": "Lunes", "tuesday": "Martes", "wednesday": "Miércoles",
    "thursday": "Jueves", "friday": "Viernes", "saturday": "Sábado", "sunday": "Domingo",
}
dias_es_abrev = {
    "monday": "Lun", "tuesday": "Mar", "wednesday": "Mié",
    "thursday": "Jue", "friday": "Vie", "saturday": "Sáb", "sunday": "Dom",
}
orden_semana = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _parsear_materias_dia(texto_bruto):
    if "||" in texto_bruto:
        materias_str, hora = texto_bruto.split("||", 1)
        hora = hora.strip()
    else:
        materias_str, hora = texto_bruto, None

    lista = []
    for parte in materias_str.strip().split("//"):
        parte = parte.strip()
        if ". " in parte:
            numero, nombre = parte.split(". ", 1)
            lista.append((numero.strip(), nombre.strip()))
        else:
            lista.append((None, parte))
    return lista, hora


materias_por_dia = {clave: _parsear_materias_dia(texto) for clave, texto in materias_colegio.items()}

DOLAR_API_URL = "https://dolarapi.com/v1/dolares"
INTERVALO_ACTUALIZACION_SEGUNDOS = 300  # 5 min
MAX_PUNTOS_HISTORIAL = 40  # cuántos puntos guarda el mini-gráfico en memoria

TIPOS_DOLAR = [
    ("oficial", "Oficial"),
    ("blue", "Blue"),
    ("bolsa", "MEP"),
    ("tarjeta", "Tarjeta"),
]

_sesion_http = requests.Session()


def obtener_cotizaciones_dolar():
    try:
        resp = _sesion_http.get(DOLAR_API_URL, timeout=6)
        resp.raise_for_status()
        cotizaciones = {}
        for item in resp.json():
            cotizaciones[item["casa"]] = {"compra": float(item["compra"]), "venta": float(item["venta"])}
        return cotizaciones, None
    except Exception as e:
        return None, str(e)


# ---------------------------------------------------------------- #
# Widgets base "Windows 11 style": esquinas redondeadas, tarjetas
# ---------------------------------------------------------------- #
class RoundedCard(BoxLayout):
    def __init__(self, bg=CARD, radius=16, **kwargs):
        super().__init__(**kwargs)
        self.radius = radius
        with self.canvas.before:
            self._color = Color(*bg)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[radius])
        self.bind(pos=self._update, size=self._update)

    def _update(self, *_a):
        self._rect.pos = self.pos
        self._rect.size = self.size

    def set_bg(self, bg):
        self._color.rgba = bg


class RoundedButton(ButtonBehavior, RoundedCard):
    """Botón con fondo redondeado y un Label centrado."""

    def __init__(self, text="", bg=CARD_ALT, fg=WHITE, radius=18, font_size=14, bold=True, **kwargs):
        super().__init__(bg=bg, radius=radius, **kwargs)
        self.label = Label(text=text, color=fg, font_size=sp(font_size), bold=bold,
                            halign="center", valign="middle")
        self.label.bind(size=lambda w, *_: setattr(w, "text_size", w.size))
        self.add_widget(self.label)

    def set_text(self, text):
        self.label.text = text

    def set_fg(self, fg):
        self.label.color = fg


class Sparkline(Widget):
    """Mini gráfico de línea con el historial de la sesión actual."""

    def __init__(self, color=GOLD, **kwargs):
        super().__init__(**kwargs)
        self.values = []
        self.line_color = color
        self.bind(pos=self._redraw, size=self._redraw)

    def set_values(self, values):
        self.values = list(values)
        self._redraw()

    def _redraw(self, *_a):
        self.canvas.clear()
        if len(self.values) < 2:
            return
        vmin, vmax = min(self.values), max(self.values)
        rng = (vmax - vmin) or 1
        n = len(self.values)
        pad = dp(4)
        pts = []
        for i, v in enumerate(self.values):
            x = self.x + (i / (n - 1)) * self.width
            y = self.y + pad + ((v - vmin) / rng) * (self.height - 2 * pad)
            pts += [x, y]
        with self.canvas:
            Color(*self.line_color)
            Line(points=pts, width=dp(1.6))


def etiqueta(texto, color=WHITE, size=16, bold=False, halign="center"):
    lbl = Label(text=texto, color=color, font_size=sp(size), bold=bold,
                halign=halign, valign="middle", size_hint_y=None)
    lbl.bind(width=lambda w, *_: setattr(w, "text_size", (w.width, None)))
    lbl.bind(texture_size=lambda w, *_: setattr(w, "height", w.texture_size[1]))
    return lbl


# ---------------------------------------------------------------- #
# Pantalla 1: Hoy
# ---------------------------------------------------------------- #
class VistaHoy(Screen):
    def __init__(self, tipo_de_dia, **kwargs):
        super().__init__(**kwargs)
        self.tipo_de_dia = tipo_de_dia
        root = ScrollView()
        col = BoxLayout(orientation="vertical", spacing=dp(14), padding=dp(20),
                         size_hint_y=None)
        col.bind(minimum_height=col.setter("height"))

        if D == 0:
            col.add_widget(etiqueta(
                "Como hoy es domingo, solo tienes que disfrutar el día. "
                "Si quieres puedes leer 20 a 30 minutos.",
                color=WHITE, size=18))
        else:
            if tipo_de_dia == 1:
                objetivo = "- Mantener, Ordenar, Prevenir Problemas, Simplificar -"
                if D == 1:
                    obj_segun_dia = ["Investigar para evitar errores", "Entender fundamentos",
                                      "Aprender buenas prácticas", "Investigar simplificaciones",
                                      "Buscar eficiencia"]
                else:
                    obj_segun_dia = ["Detectar fricción", "Reconocer pérdidas de tiempo",
                                      "Ordenar ambiente", "Optimizar sistema",
                                      "Detectar baches", "Prevenir problemas futuros"]
            else:
                objetivo = "- Crecer, Crear, Probar, Avanzar -"
                if D == 1:
                    obj_segun_dia = ["Aprender algo nuevo", "Explorar temas",
                                      "Investigar tecnologías", "Ideas de negocio",
                                      "Estructuras nuevas"]
                else:
                    obj_segun_dia = ["Pensar mejoras grandes", "Decisiones importantes",
                                      "Expansión de proyectos", "Nuevas oportunidades",
                                      "Ideas futuras", "Improvisar con creatividad"]

            col.add_widget(etiqueta(FechaActual.capitalize(), color=RED, size=30, bold=True))
            col.add_widget(etiqueta(f"Hoy toca un día de tipo {tipo_de_dia}", color=WHITE, size=24, bold=True))
            col.add_widget(etiqueta("El objetivo del día es:", color=WHITE, size=20))
            col.add_widget(etiqueta(objetivo, color=GREEN, size=20, bold=True))

            grid = GridLayout(cols=2, spacing=dp(10), size_hint_y=None)
            grid.bind(minimum_height=grid.setter("height"))
            for texto in obj_segun_dia:
                grid.add_widget(etiqueta(f"→ {texto}", color=YELLOW, size=16, halign="left"))
            col.add_widget(grid)

        root.add_widget(col)
        Clock.schedule_once(lambda *_: setattr(root, "scroll_y", 1))
        self.add_widget(root)


# ---------------------------------------------------------------- #
# Pantalla 2: Materias — selector de día en botones
# ---------------------------------------------------------------- #
class TarjetaMateria(RoundedCard):
    def __init__(self, numero, nombre, **kwargs):
        super().__init__(bg=CARD_ALT, radius=12, orientation="horizontal",
                          size_hint_y=None, height=dp(52), padding=(dp(12), 0),
                          spacing=dp(14), **kwargs)
        circulo = RoundedCard(bg=GOLD, radius=14, size_hint=(None, None), size=(dp(28), dp(28)))
        num_lbl = Label(text=numero or "•", color=BLACK, bold=True, font_size=sp(13))
        circulo.add_widget(num_lbl)
        self.add_widget(circulo)
        nombre_lbl = etiqueta(nombre, color=WHITE, size=16, halign="left")
        nombre_lbl.size_hint_y = None
        nombre_lbl.height = dp(28)
        self.add_widget(nombre_lbl)


class VistaMaterias(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dia_seleccionado = dia  # arranca en el día de hoy

        raiz = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(14))
        raiz.add_widget(etiqueta("Materias", color=RED, size=28, bold=True))

        # Fila de botones de día (Lun..Dom)
        self.fila_botones = GridLayout(cols=7, size_hint_y=None, height=dp(44), spacing=dp(6))
        self.botones = {}
        for k in orden_semana:
            b = RoundedButton(text=dias_es_abrev[k], radius=18, font_size=12,
                               bg=GOLD if k == self.dia_seleccionado else CARD_ALT,
                               fg=BLACK if k == self.dia_seleccionado else WHITE)
            b.bind(on_release=lambda _b, k=k: self.seleccionar_dia(k))
            self.botones[k] = b
            self.fila_botones.add_widget(b)
        raiz.add_widget(self.fila_botones)

        raiz.add_widget(self._divisor())

        self.panel = ScrollView()
        self._contenido_panel = BoxLayout(orientation="vertical", spacing=dp(10),
                                            size_hint_y=None, padding=(0, dp(4)))
        self._contenido_panel.bind(minimum_height=self._contenido_panel.setter("height"))
        self.panel.add_widget(self._contenido_panel)
        raiz.add_widget(self.panel)

        self.add_widget(raiz)
        self._pintar_panel(self.dia_seleccionado)
        Clock.schedule_once(lambda *_: setattr(self.panel, "scroll_y", 1))

    def _divisor(self):
        d = Widget(size_hint_y=None, height=dp(1))
        with d.canvas:
            Color(1, 1, 1, 0.15)
            self._div_rect = RoundedRectangle(pos=d.pos, size=d.size)
        d.bind(pos=lambda w, *_: setattr(self._div_rect, "pos", w.pos),
               size=lambda w, *_: setattr(self._div_rect, "size", w.size))
        return d

    def seleccionar_dia(self, dia_key):
        if dia_key == self.dia_seleccionado:
            return
        self.botones[self.dia_seleccionado].set_bg(CARD_ALT)
        self.botones[self.dia_seleccionado].set_fg(WHITE)
        self.dia_seleccionado = dia_key
        self.botones[dia_key].set_bg(GOLD)
        self.botones[dia_key].set_fg(BLACK)
        self._pintar_panel(dia_key)

    def _pintar_panel(self, dia_key):
        self._contenido_panel.clear_widgets()
        Clock.schedule_once(lambda *_: setattr(self.panel, "scroll_y", 1))
        lista_materias, hora = materias_por_dia[dia_key]

        encabezado = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(6))
        encabezado.bind(minimum_height=encabezado.setter("height"))
        encabezado.add_widget(etiqueta(dias_es[dia_key], color=WHITE, size=22, bold=True))
        if hora:
            chip = RoundedCard(bg=GOLD, radius=16, size_hint=(None, None),
                                size=(dp(140), dp(30)))
            chip.add_widget(Label(text=f"Salida {hora}", color=BLACK, bold=True, font_size=sp(13)))
            wrap = BoxLayout(size_hint_y=None, height=dp(30))
            wrap.add_widget(Widget())
            wrap.add_widget(chip)
            wrap.add_widget(Widget())
            encabezado.add_widget(wrap)
        self._contenido_panel.add_widget(encabezado)

        if len(lista_materias) == 1 and lista_materias[0][0] is None:
            self._contenido_panel.add_widget(
                etiqueta(lista_materias[0][1], color=YELLOW, size=20, bold=True))
        else:
            for numero, nombre in lista_materias:
                self._contenido_panel.add_widget(TarjetaMateria(numero, nombre))


# ---------------------------------------------------------------- #
# Pantalla 3: Finanzas — cotizaciones del dólar + mini gráfico
# ---------------------------------------------------------------- #
class FilaCotizacion(RoundedCard):
    def __init__(self, nombre, datos_tipo, historial, **kwargs):
        super().__init__(bg=CARD_ALT, radius=14, orientation="vertical",
                          size_hint_y=None, height=dp(96), padding=dp(14), spacing=dp(6),
                          **kwargs)
        fila_top = BoxLayout(size_hint_y=None, height=dp(30))
        fila_top.add_widget(etiqueta(nombre, color=WHITE, size=16, bold=True, halign="left"))

        compra_col = BoxLayout(orientation="vertical")
        compra_col.add_widget(etiqueta("Compra", color=GREY, size=11))
        compra_col.add_widget(etiqueta(f"{datos_tipo['compra']:,.2f}", color=YELLOW, size=18, bold=True))
        fila_top.add_widget(compra_col)

        venta_col = BoxLayout(orientation="vertical")
        venta_col.add_widget(etiqueta("Venta", color=GREY, size=11))
        venta_col.add_widget(etiqueta(f"{datos_tipo['venta']:,.2f}", color=YELLOW, size=18, bold=True))
        fila_top.add_widget(venta_col)

        self.add_widget(fila_top)

        spark = Sparkline(color=GOLD, size_hint_y=None, height=dp(30))
        spark.set_values(historial)
        self.add_widget(spark)


class VistaFinanzas(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        raiz = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(14))

        header = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))
        header.add_widget(Widget())
        header.add_widget(etiqueta("Cotizaciones del Dólar", color=RED, size=22, bold=True))
        self.btn_refresh = RoundedButton(text="⟳", bg=CARD_ALT, fg=WHITE, radius=20,
                                          size_hint=(None, None), size=(dp(40), dp(40)))
        header.add_widget(self.btn_refresh)
        raiz.add_widget(header)

        self.scroll = ScrollView()
        self.cuerpo = BoxLayout(orientation="vertical", spacing=dp(12), size_hint_y=None,
                                  padding=(0, dp(4)))
        self.cuerpo.bind(minimum_height=self.cuerpo.setter("height"))
        self.scroll.add_widget(self.cuerpo)
        raiz.add_widget(self.scroll)

        self.add_widget(raiz)
        self.mostrar_cargando()
        Clock.schedule_once(lambda *_: setattr(self.scroll, "scroll_y", 1))

    def mostrar_cargando(self):
        self.cuerpo.clear_widgets()
        self.cuerpo.add_widget(etiqueta("Todavía no hay datos, buscando...", color=WHITE, size=15))

    def pintar(self, datos, error_hora, historial):
        self.cuerpo.clear_widgets()
        Clock.schedule_once(lambda *_: setattr(self.scroll, "scroll_y", 1))
        if not datos:
            self.mostrar_cargando()
            return
        for casa, nombre in TIPOS_DOLAR:
            if casa in datos:
                self.cuerpo.add_widget(
                    FilaCotizacion(nombre, datos[casa], historial.get(casa, [])))
        self.cuerpo.add_widget(etiqueta(f"Último registro: {datos['hora']}", color=WHITE, size=13))
        if error_hora:
            self.cuerpo.add_widget(etiqueta(
                f"⚠ Sin conexión — mostrando el último dato disponible ({datos['hora']})",
                color=ORANGE, size=12))
        nota = etiqueta(
            "El gráfico muestra la variación registrada durante esta sesión "
            "(la API no provee historial propio).", color=GREY, size=11)
        self.cuerpo.add_widget(nota)


# ---------------------------------------------------------------- #
# Barra de navegación inferior (estilo "pill", igual a la de Flet)
# ---------------------------------------------------------------- #
class BarraNavegacion(BoxLayout):
    def __init__(self, on_change, **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(64),
                          padding=(dp(10), dp(8)), spacing=dp(8), **kwargs)
        with self.canvas.before:
            Color(*GOLD)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(20)])
        self.bind(pos=self._update, size=self._update)

        self.on_change = on_change
        self.items = {}
        for key, label in (("hoy", "Hoy"), ("materias", "Materias"), ("finanzas", "Finanzas")):
            item = RoundedButton(text=label, bg=GOLD, fg=BLACK, radius=16, font_size=13)
            item.bind(on_release=lambda _b, k=key: self._seleccionar(k))
            self.items[key] = item
            self.add_widget(item)
        self._seleccionar("hoy")

    def _update(self, *_a):
        self._rect.pos = self.pos
        self._rect.size = self.size

    def _seleccionar(self, key):
        for k, item in self.items.items():
            elegido = k == key
            item.set_bg(BLACK if elegido else GOLD)
            item.set_fg(WHITE if elegido else BLACK)
        self.on_change(key)


# ---------------------------------------------------------------- #
# App principal
# ---------------------------------------------------------------- #
class SistemaDiarioApp(App):
    def build(self):
        self.title = "Sistema Diario"
        self.store = JsonStore(self.user_data_dir + "/sistema_diario.json")
        self.historial_dolar = {casa: [] for casa, _ in TIPOS_DOLAR}

        tipo_de_dia = self._definir_tipo_de_dia()

        self.sm = ScreenManager(transition=NoTransition())
        self.vista_hoy = VistaHoy(tipo_de_dia, name="hoy")
        self.vista_materias = VistaMaterias(name="materias")
        self.vista_finanzas = VistaFinanzas(name="finanzas")
        self.sm.add_widget(self.vista_hoy)
        self.sm.add_widget(self.vista_materias)
        self.sm.add_widget(self.vista_finanzas)

        root = BoxLayout(orientation="vertical")
        root.add_widget(self.sm)
        self.nav = BarraNavegacion(on_change=self._cambiar_vista)
        nav_wrap = BoxLayout(size_hint_y=None, height=dp(80), padding=(dp(10), dp(8)))
        nav_wrap.add_widget(self.nav)
        root.add_widget(nav_wrap)

        self.vista_finanzas.btn_refresh.bind(on_release=lambda *_: self._actualizar_finanzas())

        # Estado guardado la última vez (para no arrancar en blanco sin señal)
        self._cargar_ultimo_dato_dolar()
        Clock.schedule_once(lambda *_: self._actualizar_finanzas(), 0.3)
        Clock.schedule_interval(lambda *_: self._actualizar_finanzas(),
                                 INTERVALO_ACTUALIZACION_SEGUNDOS)
        return root

    def _cambiar_vista(self, key):
        self.sm.current = key

    # ---- persistencia del "tipo de día" (equivalente a SharedPreferences) ---- #
    def _definir_tipo_de_dia(self):
        ultima_fecha = self.store.get("estado")["ultima_fecha"] if self.store.exists("estado") else None
        tipo_guardado = self.store.get("estado")["tipo_de_dia"] if self.store.exists("estado") else None

        if ultima_fecha != fecha_hoy_llave or tipo_guardado is None:
            if D == 1:
                tipo = random.choices([1, 2], weights=[0.80, 0.20], k=1)[0]
            else:
                tipo = random.choices([1, 2], weights=[0.20, 0.80], k=1)[0]
            self.store.put("estado", ultima_fecha=fecha_hoy_llave, tipo_de_dia=tipo)
            return tipo
        return int(tipo_guardado)

    # ---- persistencia / refresco de finanzas ---- #
    def _cargar_ultimo_dato_dolar(self):
        if self.store.exists("datos_dolar"):
            datos = self.store.get("datos_dolar")["datos"]
            self.vista_finanzas.pintar(datos, None, self.historial_dolar)

    def _actualizar_finanzas(self):
        threading.Thread(target=self._actualizar_finanzas_hilo, daemon=True).start()

    def _actualizar_finanzas_hilo(self):
        ahora = datetime.now()
        hora_str = ahora.strftime("%H:%M")
        cotizaciones, error = obtener_cotizaciones_dolar()

        def aplicar(_dt):
            if error is None:
                cotizaciones["hora"] = hora_str
                for casa, _ in TIPOS_DOLAR:
                    if casa in cotizaciones:
                        hist = self.historial_dolar.setdefault(casa, [])
                        hist.append(cotizaciones[casa]["venta"])
                        del hist[:-MAX_PUNTOS_HISTORIAL]
                self.store.put("datos_dolar", datos=cotizaciones)
                self.vista_finanzas.pintar(cotizaciones, None, self.historial_dolar)
            else:
                datos_previos = None
                if self.store.exists("datos_dolar"):
                    datos_previos = self.store.get("datos_dolar")["datos"]
                self.vista_finanzas.pintar(datos_previos, hora_str, self.historial_dolar)

        Clock.schedule_once(aplicar)


if __name__ == "__main__":
    SistemaDiarioApp().run()