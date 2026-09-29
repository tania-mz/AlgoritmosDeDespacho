import math
from collections import deque
import re

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
        # Orden FIJO de los turnos: por llegada (empate: el orden en que se ingresaron)
        orden = sorted(self.procesos, key=lambda p: p.llegada)  # sorted es estable
        restante = {p: p.rafaga for p in orden}  # NO se toca p.rafaga
        segmentos = []
        tiempo, pos = 0, 0  # pos = posición del 'orden' donde se busca el próximo turno

        while any(r > 0 for r in restante.values()):
            # Desde 'pos' y dando la vuelta, el primer proceso que ya llegó y no ha terminado
            elegido = None
            for k in range(len(orden)):
                idx = (pos + k) % len(orden)
                if restante[orden[idx]] > 0 and orden[idx].llegada <= tiempo:
                    elegido, pos = orden[idx], idx
                    break
            if elegido is None:  # nadie ha llegado: el reloj salta a la próxima llegada
                tiempo = min(p.llegada for p in orden if restante[p] > 0)
                continue

            uso = min(self.quantum, restante[elegido])
            segmentos.append((elegido.nombre, tiempo, tiempo + uso))
            tiempo += uso
            restante[elegido] -= uso
            pos = (pos + 1) % len(orden)  # el siguiente turno sigue el orden fijo

        return segmentos, self._metricas_por_round(segmentos)
    
    def esperasPorRound(self, segmentos):
        referencia = {p.nombre: p.llegada for p in self.procesos}  # desde cuándo espera
        resultado = {}
        for nombre, inicio, fin in segmentos:   # segmentos vienen en orden cronológico
            resultado.setdefault(nombre, []).append(inicio - referencia[nombre])
            referencia[nombre] = fin            # el próximo round espera desde aquí
        return resultado

    def _metricas_por_round(self, segmentos):
        """Espera total = suma de las esperas de todos sus rounds."""
        por_round = self.esperasPorRound(segmentos)
        metricas = []
        for p in self.procesos:
            espera = sum(por_round[p.nombre])
            sistema = self.calcularTiempoSistema(p, espera)
            metricas.append((p.nombre, espera, sistema))
        return metricas