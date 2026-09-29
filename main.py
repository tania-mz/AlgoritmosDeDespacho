import tkinter as tk
from tkinter import ttk, messagebox
 
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import MaxNLocator
 
from algoritmos import Proceso, ProcesoPrioridad, FIFO, SJF, Prioridad, RoundRobin
 
ALGORITMOS = ["FIFO", "SJF", "Priority", "Round Robin"]
COLORES = ["#4C78A8", "#F58518", "#54A24B", "#E45756", "#72B7B2",
           "#B279A2", "#FF9DA6", "#9D755D", "#BAB0AC", "#EECA3B"]
VERDE_FONDO = "#E3F6E5"    # fondo de la pantalla de inicio (verde clarito)
VERDE_BOTON = "#A8E0AE"    # botones
VERDE_HOVER = "#8FD397"    # botones al pasar el mouse
 
 
# ----------------------------------------------------------------------
# VENTANA PRINCIPAL: alterna entre el menú y el simulador
# ----------------------------------------------------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Simulador de algoritmos de despacho")
        self.geometry("1150x700")
        self.pantalla = None  # pantalla que se está mostrando
        self.mostrar_menu()
 
    def _cambiar_pantalla(self, nueva):
        """Destruye la pantalla actual y muestra la nueva."""
        if self.pantalla is not None:
            self.pantalla.destroy()
        self.pantalla = nueva
        self.pantalla.pack(fill="both", expand=True)
 
    def mostrar_menu(self):
        """Pantalla inicial: un botón por algoritmo, sobre fondo verde clarito."""
        marco = tk.Frame(self, bg=VERDE_FONDO)
        tk.Label(marco, text="Algoritmos de despacho", bg=VERDE_FONDO, font=("Arial", 22, "bold")).pack(pady=(90, 8))
        tk.Label(marco, text="Elige el algoritmo que quieres ver", bg=VERDE_FONDO, font=("Arial", 12)).pack(pady=(0, 30))
        for nombre in ALGORITMOS:
            tk.Button(marco, text=nombre, width=26, font=("Arial", 12), bg=VERDE_BOTON, activebackground=VERDE_HOVER, relief="flat", cursor="hand2",command=lambda n=nombre: self.mostrar_simulador(n)).pack(pady=8, ipady=8)
        self._cambiar_pantalla(marco)
 
    def mostrar_simulador(self, algoritmo):
        """Abre el simulador del algoritmo elegido."""
        self._cambiar_pantalla(Simulador(self, algoritmo, self.mostrar_menu))
 
 
# ----------------------------------------------------------------------
# PANTALLA DEL SIMULADOR
# ----------------------------------------------------------------------
class Simulador(ttk.Frame):
    def __init__(self, master, algoritmo, volver):
        super().__init__(master)
        self.algoritmo = algoritmo   # nombre del algoritmo elegido
        self.volver = volver         # función para regresar al menú
        self.procesos = []           # objetos Proceso cargados por el usuarios
        self._crear_panel_izquierdo()
        self._crear_panel_derecho()
        self.actualizar()
 
    # ------------------------- Construcción de la UI -------------------
    def _crear_panel_izquierdo(self):
        """Formulario de entrada + tabla de procesos."""
        izq = ttk.Frame(self, padding=10)
        izq.pack(side="left", fill="y")
        ttk.Label(izq, text=f"Algoritmo: {self.algoritmo}",
                font=("Arial", 14, "bold")).pack(anchor="w", pady=(0, 10))
 
        # Campos: la prioridad solo aparece en Priority
        self.campos = ["Nombre", "Ráfaga de CPU", "Tiempo de llegada"]
        if self.algoritmo == "Priority":
            self.campos.append("Prioridad")
 
        form = ttk.Frame(izq)
        form.pack(fill="x")
        self.entradas = {}
        for fila, campo in enumerate(self.campos):
            ttk.Label(form, text=campo).grid(row=fila, column=0, sticky="w", pady=3)
            entrada = ttk.Entry(form, width=14)
            entrada.grid(row=fila, column=1, padx=8)
            entrada.bind("<Return>", self.agregar)  # Enter agrega el proceso
            self.entradas[campo] = entrada
        # Flechas ↑ y ↓ para moverse entre casillas
        orden = [self.entradas[c] for c in self.campos]
        for i, casilla in enumerate(orden):
            if i < len(orden) - 1:
                casilla.bind("<Down>", lambda e, sig=orden[i + 1]: sig.focus())
            if i > 0:
                casilla.bind("<Up>", lambda e, ant=orden[i - 1]: ant.focus())
        self.entradas["Nombre"].focus()
 
        # El quantum es un único valor para todo Round Robin
        self.spin_quantum = None
        if self.algoritmo == "Round Robin":
            ttk.Label(form, text="Quantum").grid(row=len(self.campos), column=0, sticky="w", pady=3)
            self.spin_quantum = ttk.Spinbox(form, from_=1, to=100, width=12, command=self.actualizar)
            self.spin_quantum.set(2)
            self.spin_quantum.grid(row=len(self.campos), column=1, padx=8)
            self.spin_quantum.bind("<KeyRelease>", lambda e: self.actualizar())
 
        botones = ttk.Frame(izq)
        botones.pack(fill="x", pady=10)
        ttk.Button(botones, text="Agregar (Enter)", command=self.agregar).pack(side="left")
        ttk.Button(botones, text="Eliminar seleccionado", command=self.eliminar).pack(side="left", padx=6)
        ttk.Button(botones, text="Limpiar todo", command=self.limpiar).pack(side="left")
 
        # Tabla con los procesos ingresados
        self.tabla = ttk.Treeview(izq, columns=self.campos, show="headings", height=14)
        for c in self.campos:
            self.tabla.heading(c, text=c)
            self.tabla.column(c, width=95, anchor="center")
        self.tabla.pack(fill="y", expand=True) 
        self.tabla.bind("<Delete>", self.eliminar)   
 
        ttk.Button(izq, text="← Volver al menú", command=self.volver).pack(anchor="w", pady=(10, 0))
 
    def _crear_panel_derecho(self):
        """Gráfica de Gantt (arriba) y tabla de tiempos (abajo)."""
        der = ttk.Frame(self, padding=10)
        der.pack(side="right", fill="both", expand=True)
 
        # Figura de Matplotlib incrustada en Tkinter
        self.figura = Figure(figsize=(6, 3.6), dpi=100)
        self.ejes = self.figura.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figura, master=der)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
 
        # Cantidad de rounds (solo Round Robin)
        self.lbl_rounds = ttk.Label(der, font=("Arial", 11, "bold"))
        if self.algoritmo == "Round Robin":
            self.lbl_rounds.pack(anchor="w", pady=(6, 0))
 
        # Tabla de tiempos de espera y de sistema
        cols = ("Proceso", "Tiempo de espera", "Tiempo de sistema")
        self.tabla_tiempos = ttk.Treeview(der, columns=cols, show="headings", height=6)
        for c in cols:
            self.tabla_tiempos.heading(c, text=c)
            self.tabla_tiempos.column(c, anchor="center")
        self.tabla_tiempos.pack(fill="x", pady=6)
        self.lbl_promedios = ttk.Label(der)
        self.lbl_promedios.pack(anchor="w")
 
    # ------------------------- Acciones del usuario --------------------
    def _entero(self, campo):
        """Lee un campo y lo convierte a entero (o lanza ValueError claro)."""
        try:
            return int(self.entradas[campo].get().strip())
        except ValueError:
            raise ValueError(f"'{campo}' debe ser un número entero.")
 
    def agregar(self, evento=None):
        """Valida los datos, crea el Proceso y actualiza tabla y gráfica."""
        try:
            nombre = self.entradas["Nombre"].get().strip()
            if not nombre:
                raise ValueError("El nombre no puede estar vacío.")
            if any(p.nombre == nombre for p in self.procesos):
                raise ValueError("Ya existe un proceso con ese nombre.")
            rafaga = self._entero("Ráfaga de CPU")
            llegada = self._entero("Tiempo de llegada")
            if rafaga <= 0:
                raise ValueError("La ráfaga debe ser mayor que 0.")
            if llegada < 0:
                raise ValueError("El tiempo de llegada no puede ser negativo.")
            if self.algoritmo == "Priority":
                proceso = ProcesoPrioridad(nombre, rafaga, llegada, self._entero("Prioridad"))
            else:
                proceso = Proceso(nombre, rafaga, llegada)
        except ValueError as error:
            messagebox.showwarning("Dato inválido", str(error))
            return

        self.procesos.append(proceso)
        self.tabla.insert("", "end", values=[e.get().strip() for e in self.entradas.values()])
        self._limpiar_formulario()
        self.actualizar()
 
    def limpiar(self):
        """Borra todos los procesos."""
        self.procesos.clear()
        self.tabla.delete(*self.tabla.get_children())
        self.actualizar()

    def eliminar(self, evento=None):
        """Elimina el proceso seleccionado en la tabla."""
        seleccion = self.tabla.selection()
        if not seleccion:
            messagebox.showinfo("Eliminar", "Primero selecciona un proceso de la tabla.")
            return
        indice = self.tabla.index(seleccion[0])   # la fila tiene la misma posición que en self.procesos
        del self.procesos[indice]
        self.tabla.delete(seleccion[0])
        self.actualizar()                         # redibuja la gráfica y recalcula los tiempos

    def _limpiar_formulario(self):
        """Vacía las casillas y deja el cursor en 'Nombre'."""
        for e in self.entradas.values():
            e.delete(0, "end")
        self.entradas["Nombre"].focus()
 
    # ------------------------- Cálculo y dibujo ------------------------
    def _crear_algoritmo(self):
        """Crea el objeto del algoritmo elegido; None si el quantum es inválido."""
        if self.algoritmo == "FIFO":
            return FIFO()
        if self.algoritmo == "SJF":
            return SJF()
        if self.algoritmo == "Priority":
            return Prioridad()
        try:
            quantum = int(self.spin_quantum.get())
            return RoundRobin(quantum) if quantum > 0 else None
        except ValueError:
            return None
 
    def actualizar(self):
        """Recalcula con los procesos actuales y redibuja todo."""
        alg = self._crear_algoritmo()
        if alg is None:
            self.lbl_rounds.config(text="Quantum inválido (entero mayor que 0)")
            return
        for p in self.procesos:
            alg.agregar(p)
        segmentos, metricas = alg.ejecutar()

        self._dibujar_gantt(segmentos)
        if self.algoritmo == "Round Robin":
            self._llenar_tiempos_round(alg, segmentos, metricas)
            self.lbl_rounds.config(text=f"Cantidad de rounds: {alg.calcularRounds()}")
        else:
            self._llenar_tiempos(metricas)

    def _dibujar_gantt(self, segmentos):
        """Un proceso por fila; cada tramo de ejecución es una barra horizontal."""
        ax = self.ejes
        ax.clear()
        if not self.procesos:
            ax.text(0.5, 0.5, "Agrega un proceso para ver la gráfica",
                    ha="center", va="center", transform=ax.transAxes)
            ax.set_xticks([])
            ax.set_yticks([])
        else:
            for fila, p in enumerate(self.procesos):
                # broken_barh recibe [(inicio, duración), ...]: sirve para RR,
                # donde un proceso tiene varios tramos
                tramos = [(ini, fin - ini) for n, ini, fin in segmentos if n == p.nombre]
                ax.broken_barh(tramos, (fila - 0.35, 0.7), facecolors=COLORES[fila % len(COLORES)], edgecolor="black")
            ax.set_yticks(range(len(self.procesos)))
            ax.set_yticklabels([p.nombre for p in self.procesos])
            ax.set_ylim(len(self.procesos) - 0.5, -0.5)  # primer proceso arriba
            ax.set_xlim(0, max(fin for _, _, fin in segmentos))
            ax.xaxis.set_major_locator(MaxNLocator(integer=True))
            ax.set_xlabel("Tiempo (s)")
            ax.set_ylabel("Procesos")
            ax.grid(axis="x", linestyle="--", alpha=0.5)
        ax.set_title(f"Diagrama de Gantt - {self.algoritmo}")
        self.figura.tight_layout()
        self.canvas.draw()
 
    def _llenar_tiempos(self, metricas):
        """Tabla de tiempos para FIFO, SJF y Priority."""
        self.tabla_tiempos.delete(*self.tabla_tiempos.get_children())
        for fila in metricas:
            self.tabla_tiempos.insert("", "end", values=fila)
        self._mostrar_promedios(metricas)

    def _llenar_tiempos_round(self, alg, segmentos, metricas):
        """Tabla de Round Robin: una columna de espera por cada round."""
        self.tabla_tiempos.delete(*self.tabla_tiempos.get_children())
        n = alg.calcularRounds()   # cantidad de columnas TERound
        cols = (["Proceso"] + [f"TERound {i}" for i in range(1, n + 1)]
                + ["Tiempo de espera", "Tiempo de sistema"])
        self.tabla_tiempos["columns"] = cols   # las columnas cambian según los rounds
        for c in cols:
            self.tabla_tiempos.heading(c, text=c)
            self.tabla_tiempos.column(c, anchor="center", width=90, minwidth=60)

        por_round = alg.esperasPorRound(segmentos)
        for nombre, espera, sistema in metricas:
            esperas = por_round[nombre]
            celdas = esperas + ["-"] * (n - len(esperas))   # "-" si terminó antes
            self.tabla_tiempos.insert("", "end", values=[nombre, *celdas, espera, sistema])
        self._mostrar_promedios(metricas)

    def _mostrar_promedios(self, metricas):
        """Promedio de espera y de sistema (suma de totales / cantidad de procesos)."""
        if metricas:
            prom_e = sum(m[1] for m in metricas) / len(metricas)
            prom_s = sum(m[2] for m in metricas) / len(metricas)
            self.lbl_promedios.config(
                text=f"Promedio de espera: {prom_e:.2f}    Promedio de sistema: {prom_s:.2f}")
        else:
            self.lbl_promedios.config(text="")
 
 
if __name__ == "__main__":
    App().mainloop()
 