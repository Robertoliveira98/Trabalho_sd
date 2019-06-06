import socket
import struct
import select
import sys
import os
import netifaces
import pickle
import time as t
from threading import Thread
from random import randint


INICIA_ELEICAO = 10
RESPOSTA_ELEICAO = 20
LIDER_ATUAL = 30
INICIA_BERKELEY = 40
RESPOSTA_BERKELEY = 50
AJUSTE_BERKELEY = 60
TERMINA_COMUNICACAO = 99

TODOS = 0

GRUPO_MC = '224.0.0.0'
PORTA = 8888
PID = str(os.getpid())

global ehLider
global liderId
global timeList
global tempoAtual
global ultimoId
global stop

ehLider = False
liderId = ''
timeList = []
tempoAtual = 0
ultimoId = []
stop = False


class Mensagem():
	def __init__(self, action, msg, remetenteId, destinoId):
		self.action = action
		self.msg = msg
		self.remetenteId = remetenteId
		self.destinoId = destinoId



#-----------GERENCIAR MENSAGENS

def receive_message():
	#print('Lendo mensagem...', )
	serial_data, sender_addr = mySocket.recvfrom(512)
	received_data = pickle.loads(serial_data)

	global tempoAtual
	global ehLider
	if received_data.remetenteId != myId: #impede que leia uma mensagem enviada por ele msm
		if received_data.action == INICIA_ELEICAO:
			print('')
			print('Pedido de eleição recebido.')
			if int(PID) > int(received_data.msg): #se for maior inicia bully dnv
				print('\n\nTem PID maior (', PID, ' > ', int(received_data.msg), '). Enviando resposta.')
				response = Mensagem(RESPOSTA_ELEICAO, 0, myId, received_data.remetenteId)
				serial_response = pickle.dumps(response)
				mySocket.sendto(serial_response, (GRUPO_MC, PORTA))
				startBully();
				return (INICIA_ELEICAO, True)

			print('') #se for menor n faz nada
			print('Tem PID menor (', PID, ' < ', int(received_data.msg), '). NAO envia nada.')
			return (INICIA_ELEICAO, False)

		elif received_data.action == RESPOSTA_ELEICAO: #retorna para bully
			print('Rebendo resposta de eleição.')
			return (RESPOSTA_ELEICAO, True, received_data.destinoId)

		elif received_data.action == LIDER_ATUAL:
			print('Definindo novo lider para: ', received_data.msg)
			liderId = received_data.msg
			return (LIDER_ATUAL, True)

		elif received_data.action == INICIA_BERKELEY:
			ajuste = tempoAtual - received_data.msg
			print('')
			print('----------------------------------------------------------')
			print('Pedido de valor de Atraso para o algoritmo de Berkeley.')
			print('Tempo atual: ', tempoAtual,' - Atraso enviado: ', ajuste, '.')
			print('----------------------------------------------------------')
			response = Mensagem(RESPOSTA_BERKELEY, ajuste, myId, TODOS)
			serial_response = pickle.dumps(response)
			mySocket.sendto(serial_response, (GRUPO_MC, PORTA))
			return (INICIA_BERKELEY, True)

		elif (received_data.action == RESPOSTA_BERKELEY) & (ehLider == True): #se for o lider recebe atrasos
			print('')
			print('Adiciona o atraso do escravo à lista de tempo (', received_data.msg, ').')
			timeList.append((sender_addr, received_data.msg))
			global ultimoId
			ultimoId.append(received_data.remetenteId)
			return (RESPOSTA_BERKELEY, True)

		elif received_data.action == AJUSTE_BERKELEY:
			if received_data.destinoId == myId:
				print('')
				print('')
				print('----------------------------------------------------------')
				print('Ajusta o tempo de acordo com o enviado pelo lider (', received_data.msg,').')
				print(' - Tempo antes do ajuste: ', tempoAtual, '.')
				tempoAtual = received_data.msg + tempoAtual
				print(' - Tempo ajustado: ', tempoAtual, '.')
				print('----------------------------------------------------------')
				print('')
				print('Lendo mensagens...')
				print('')
				return (AJUSTE_BERKELEY, True)
		elif received_data.action == TERMINA_COMUNICACAO:
			print('')
			print('FIM')
			print('')
			global stop
			stop = True
			sys.exit(0)
		else:
			return None
	else:
		return (None, None)


#--------------BULLY

def startBully():
	global ehLider
	print('')
	print('Iniciando eleição.')
	msg = Mensagem(INICIA_ELEICAO, PID, myId, TODOS)
	serial_data = pickle.dumps(msg)
	print('Enviando para todos em multicast.')
	mySocket.sendto(serial_data, (GRUPO_MC, PORTA))

	print('Esperando respostas.')
	timeoutMark = t.time() + 1.0
	while True:
		timeOut = timeoutMark - t.time()
		if timeOut > 0:
			readables, writeables, exceptions = select.select([mySocket], [], [mySocket], timeOut)
		else:
			print('')
			print('Timout: não houve resposta. Torna-se lider.')
			ehLider = True
			liderId = myId
			enviaLider()
			startBerkeley()
			break

		if readables:
			received_data = receive_message()

			if received_data[0] == RESPOSTA_ELEICAO:
<<<<<<< HEAD
				if received_data[2] == myId: #verifica se a mensagem eh para ele
=======
				if received_data[2] == myId:
>>>>>>> cfe6e26e04785fa66a04b3a14a36d9ae458eabad
					print('Não é lider. Há um PID maior.')
				ehLider = False
				while True:
					receive_message()
				break


#------ANUNCIAR LIDER

def enviaLider():
	print('Enviando mensagem em multicast anunciando novo lider.')
	msg = Mensagem(LIDER_ATUAL, myId, myId, TODOS)
	serial_data = pickle.dumps(msg)
	mySocket.sendto(serial_data, (GRUPO_MC, PORTA))


#----------BERKELEY

def startBerkeley():
	global tempoAtual
	print('')
	print('Inicia o algoritmo de Berkeley.\n\nEnvia mensagem em multicast com o tempo do lider (', tempoAtual, ').')
	msg = Mensagem(INICIA_BERKELEY, tempoAtual, myId, TODOS)
	serial_data = pickle.dumps(msg)
	mySocket.sendto(serial_data, (GRUPO_MC, PORTA))

	print('Esperando respostas.')
	timeoutMark = t.time() + 1.0 # 1s de espera
	while True:
		timeOut = timeoutMark - t.time()
		if timeOut > 0:
			readables, writeables, exceptions = select.select([mySocket], [], [mySocket], timeOut)
		else:
			break

		if readables:
			receive_message()

	print('')
	print('Calcula dos ajustes.')
	somaAtrasos = 0

	for _, time in timeList:
		somaAtrasos += int(time)

	mediaAtrasos = int(somaAtrasos / (len(timeList) + 1))

	print('Envia os ajustes aos escravos.')
	for _, time in timeList:
		ajuste = mediaAtrasos - int(time)
		global ultimoId
		msg = Mensagem(AJUSTE_BERKELEY, ajuste, myId, ultimoId[0])
		ultimoId.pop(0)
		serial_data = pickle.dumps(msg)
		mySocket.sendto(serial_data, (GRUPO_MC, PORTA))
	timeList.clear()
	print('')
	print('----------------------------------------------------------')
	print(' - Tempo antes do ajuste: ', tempoAtual, '.')
	tempoAtual += mediaAtrasos
	print(' - Tempo ajustado: ', tempoAtual, '.')
	ultimoId.clear();
	print('----------------------------------------------------------')
	print('')
	while True:
		aux = int (input('0 para Berkeley e 1 para terminar\n'))
		if aux == 0:
			startBerkeley()
		else:
			msg = Mensagem(TERMINA_COMUNICACAO, 0, myId, TODOS)
			serial_data = pickle.dumps(msg)
			mySocket.sendto(serial_data, (GRUPO_MC, PORTA))
			print('')
			print('FIM')
			print('')
			global stop
			stop = True
			sys.exit(0)


#-----------------RELOGIO

def start_clock():
	global tempoAtual
	global stop
<<<<<<< HEAD
=======
	# timeStep = randint(1,5)
>>>>>>> cfe6e26e04785fa66a04b3a14a36d9ae458eabad
	timeStep = 1
	stop = False
	while stop == False:
		tempoAtual += timeStep
		t.sleep(0.75)


#--------------------MAIN

mySocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
mySocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 2)
mySocket.bind((GRUPO_MC, PORTA))
mreq = struct.pack("4sl", socket.inet_aton(GRUPO_MC), socket.INADDR_ANY)
mySocket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

myId = 3
print('IP: ', myId)
print('PID: ', PID)

Thread(target = start_clock).start()

print('')
print('Lendo mensagens...')
print('')

while True:
	receive_message()
