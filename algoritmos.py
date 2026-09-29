import math
from collections import deque

# ----------------------------------------------------------------------
# PROCESOS (los datos que llena el usuario)
# ----------------------------------------------------------------------
class Proceso:
    def __init__(self, nombre, rafaga, llegada):
        self.nombre = nombre    # identificador, ej. "P1"
        self.rafaga = rafaga    # tiempo de CPU que necesita
        self.llegada = llegada  # instante en que llega al sistema
 
class ProcesoPrioridad(Proceso):
    def __init__(self, nombre, rafaga, llegada, prioridad):
        super().__init__(nombre, rafaga, llegada)  # reutiliza el constructor del padre
        self.prioridad = prioridad
 
# ----------------------------------------------------------------------
# CLASE PADRE
# ----------------------------------------------------------------------
class Algoritmo: 
    def __init__(self):
        self.procesos = []
 
    def agregar(self, proceso):
        self.procesos.append(proceso)
 
    def ejecutar(self):
        raise NotImplementedError
 
    # --- Cálculos compartidos por todos los algoritmos -----------------
    def calcularTiempoEspera(self, proceso, tiempo_salida):
        return tiempo_salida - proceso.llegada - proceso.rafaga
 
    def calcularTiempoSistema(self, proceso, tiempo_espera):
        return tiempo_espera + proceso.rafaga
 
    def _metricas(self, salidas):
        metricas = []
        for p in self.procesos:
            espera = self.calcularTiempoEspera(p, salidas[p])
            sistema = self.calcularTiempoSistema(p, espera)
            metricas.append((p.nombre, espera, sistema))
        return metricas
 
    def _despachar_no_apropiativo(self, clave):
        pendientes = list(self.procesos)
        tiempo, segmentos, salidas = 0, [], {}
 
        while pendientes:
            listos = [p for p in pendientes if p.llegada <= tiempo]
            if not listos:  # CPU libre: el reloj salta a la próxima llegada
                tiempo = min(p.llegada for p in pendientes)
                continue
            elegido = min(listos, key=clave)
            inicio = tiempo
            tiempo += elegido.rafaga
            segmentos.append((elegido.nombre, inicio, tiempo))
            salidas[elegido] = tiempo
            pendientes.remove(elegido)
 
        return segmentos, self._metricas(salidas)
 
 
# ----------------------------------------------------------------------
# ALGORITMOS
# ----------------------------------------------------------------------
class FIFO(Algoritmo):
    def ejecutar(self):
        return self._despachar_no_apropiativo(lambda p: p.llegada)
 
 
class SJF(Algoritmo):
    def ejecutar(self):
        return self._despachar_no_apropiativo(lambda p: (p.rafaga, p.llegada))
 
 
class Prioridad(Algoritmo):
    def ejecutar(self):
        return self._despachar_no_apropiativo(lambda p: (p.prioridad, p.llegada))
 
 
class RoundRobin(Algoritmo):
    def __init__(self, quantum):
        super().__init__()  # crea self.procesos
        self.quantum = quantum
 
    def calcularRounds(self):
        if not self.procesos:
            return 0
        return math.ceil(max(p.rafaga for p in self.procesos) / self.quantum)
 
    def ejecutar(self):
        por_llegar = sorted(self.procesos, key=lambda p: p.llegada)  # estable
        restante = {p: p.rafaga for p in self.procesos}  # NO se toca p.rafaga
        cola, segmentos, salidas = deque(), [], {}
        tiempo, i = 0, 0
 
        def admitir():
            nonlocal i
            while i < len(por_llegar) and por_llegar[i].llegada <= tiempo:
                cola.append(por_llegar[i])
                i += 1
 
        while cola or i < len(por_llegar):
            if not cola:  # CPU libre: salta a la próxima llegada
                tiempo = max(tiempo, por_llegar[i].llegada)
            admitir()
            p = cola.popleft()
            uso = min(self.quantum, restante[p])
            segmentos.append((p.nombre, tiempo, tiempo + uso))
            tiempo += uso
            restante[p] -= uso
            admitir()  # los que llegaron mientras corría entran antes que p
            if restante[p] > 0:
                cola.append(p)      # vuelve al final de la cola
            else:
                salidas[p] = tiempo  # terminó
 
        return segmentos, self._metricas(salidas)
 