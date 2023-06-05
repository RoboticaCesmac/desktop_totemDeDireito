from random import randint
from datetime import datetime
from ReproducaoVideo import ReproducaoVideo
from threading import Thread 
from boot import boot
import struct
import os
import requests
import json
import time
import platform
import datetime as dt
# BIBLIOTECAS INSTALADAS POR FORA
from analise_palavras import AnalisePalavras
from playsound import playsound
from firebase_admin import credentials
from firebase_admin import db
from dotenv import load_dotenv
from vosk import Model, KaldiRecognizer
import firebase_admin
import speech_recognition
import pvporcupine
import pyaudio
import keyboard
from gtts import gTTS
import openai
import ConectaVision

# Registra o que foi falado na ultima interação
escutado = None

# Motores disponíveis: vosk | speechrecognition
# Desempenho de acertos do VOSK: 46.66% | Desempenho do SpeechRecognition: 93.33% (baseado em um teste com 3 tentativas por comando, total de 45 comandos)
# O vosk permite uma velocidade de processamento ultra rápida, enquanto o speechrecognition é mais lento
# O vosk é muito impreciso ao detectar diálogos, enquanto o speechrecognition é extremamente preciso
# Vantagens vosk: Ultra-Rápido
# Vantagens speechrec: Ultra-Preciso
motor_reconhecimento = "speechrecognition"
# Define qual é a I.A que irá assumir o controle - conecta ou totem
inteligencia = "conecta"

# Inicializa os recursos utilizados
load_dotenv() # Carrega o plug-in do dotenv

if(platform.system() == "Windows"):
    if inteligencia=="conecta":# Caminho da palavra de ativação
        keyword_paths = ['picovoice/conecta_pt_windows_v2_1_0.ppn']
    if inteligencia=="totem":
        keyword_paths = ["picovoice/ei-totem_pt_windows_v2_1_0.ppn"]
else:
    keyword_paths = ['picovoice/conecta_pt_raspberry-pi_v2_1_0.ppn']
model_path = "picovoice/porcupine_params_pt.pv" # Modelo pt-pt

porcupine = None # Variáveis utilizadas pelo porcupine
pa = None # Variáveis utilizadas pelo porcupine
audio_stream = None # Variáveis utilizadas pelo porcupine
threadSom = False # Thread de diálogo pela rede firebase
parar = False # False = não escuta - True = escutando
numeroRespostas = 0 # Determina quando a I.A não entende
keyword_index = -1 #quando maior que 0, é por que o picovoice detectou uma palavra de ativação
estaFalando = False # define quando o robô está falando
falandoViaFirebase = False # Quando verdadeiro, faz com que o robô fale uma frase gravada no firebase via app
escutarDoFirebase = False # Quando verdadeiro, permite que interaja com o robô por texto a partir do Firebase, ignorando o reconhecimento de voz
ignorarPicovoice = False # Quando verdadeiro, permite ignorar a palavra de ativação "ei totem" ou "conecta"
"""
É uma função que faz o robô falar uma frase que pode ser gravada no firebase pelo app, além de verificar se alguém interagiu por texto
"""
def verificarFalaNoFirebase():
    global falandoViaFirebase
    global escutarDoFirebase
    global ignorarPicovoice
    while True:
        # verifica se foi solicitado que o totem fale algo pelo firebase
        falaViaFirebase = db.reference("Conecta").child("fala").child("falar").get()
        escutarDoFirebase = db.reference("Conecta").child("escuta").child("escutar").get()
        ignorarPicovoice = db.reference("Conecta").child("ignorar").get()
        if ignorarPicovoice == True:
            db.reference("Conecta").child("ignorar").set(False)
        if falaViaFirebase == True:
            falandoViaFirebase = True
            setarExpressao("respondendo")
            playsound("audios/awake.mp3")
            falar([db.reference("Conecta").child("fala").child("texto").get()])
            playsound("audios/sleep.mp3")
            falandoViaFirebase = False
            db.reference("Conecta").child("fala").child("falar").set(False)
            db.reference("Conecta").child("fala").child("texto").set("")
            



"""
Inicia uma thread para o um áudio que serve para o microfone reconhecer o som do ambiente
"""
def startAudioVerificador():
    thread = Thread(target=verificarSom, args=())
    thread.daemon = True  # https://stackoverflow.com/questions/11815947/cannot-kill-python-script-with-ctrl-c
    thread.start()

"""
Reproduz um áudio que o próprio microfone identificará para reconhecer o som do ambiente
"""
def verificarSom():
    try:
        playsound("audios/thinking.mp3")
    except:
        print(" \033[32m[LOG]\033[0;0m \033[32m[ERR]\033[0;0m erro no som")
    


"""
Inicia uma thread para o áudio de pensamento
"""
def startAudioThread():
    thread = Thread(target=pensar, args=())
    thread.daemon = True  # https://stackoverflow.com/questions/11815947/cannot-kill-python-script-with-ctrl-c
    thread.start()
    
"""
Reproduz áudio quando está pensando
"""
def pensar():
    while pensando == True:
        try:
            playsound("audios/thinking.mp3")
        except:
            print(" \033[32m[LOG]\033[0;0m \033[32m[ERR]\033[0;0m erro no som")

"""
Reproduz em audio o texto passado por parâmetro
"""
def falar(textos):
    if(len(textos) > 0):
        texto = textos[randint(0,len(textos)-1)]   # Escolhe um texto dentre vários
        #pyttsx3 utiliza a voz instalada no pc, no caso do Windows: Microsoft Daniel (totem) ou Microsoft Maria (Conecta)
        if(platform.system() == "Windows"):
            from sintetizador import _TTS
            tts = _TTS(inteligencia)
            tts.start(texto)
            del(tts)


        else: #linux utilizará o gtts para sintetizar uma voz feminina igual a do Google, (Conecta)
            tts = gTTS(text=texto, lang='pt-br')
            filename = "audio.mp3"
            tts.save(filename)
            playsound(filename)
            os.remove(filename)
    
        
        print(" \033[32m[LOG]\033[0;0m Eu falei: "+texto)


"""
Fica escutando o microfone e chama a função de entender o que foi falado quando é reconhecido algum som
"""
def escutarMicrofone():
    global escutarDoFirebase
    global pyAudio
    global voskRecognizer
    textoFalado = ""

    # ignora a escuta do microfone se for solicitado uma interação pelo sistema web/firebase
    if escutarDoFirebase == True:
        textoFalado = db.reference("Conecta").child("escuta").child("texto").get()
        db.reference("Conecta").child("escuta").child("escutar").set(False)
        db.reference("Conecta").child("escuta").child("texto").set("")
        escutarDoFirebase = False
    # escuta o microfone
    else:
        if motor_reconhecimento == "speechrecognition":
            presentDate = dt.datetime.now() # pega a data atual 
            unix_timestamp = dt.datetime.timestamp(presentDate)*1000 # transforma a data em unix timestamp
            unix_timestamp = int(str(int(unix_timestamp))[:-3]) # formata o unix para retirar milésimos
            
            while textoFalado == "": 
                presentDate = dt.datetime.now() # pega a data atual

                if int(str(int(dt.datetime.timestamp(presentDate)*1000))[:-3]) - 15 > unix_timestamp: #compara a data atual com a anterior em unix time e para a execução caso passe 15 segundos sem entender nada
                    global parar
                    parar = True # Para de escutar e dorme
                    global numeroRespostas
                    numeroRespostas = numeroRespostas + 1 # Impede que peça desculpas por não ter entendido
                    print(" \033[33m[WARN]\033[0;0m Microfone desligado por inatividade")
                    break

                with speech_recognition.Microphone() as origemAudio:
                    print(" \033[32m[LOG]\033[0;0m Escutando microfone...")
                    audioEscutado = recognizer.listen(origemAudio)#, phrase_time_limit=5.0) # escuta o microfone
                    global pensando
                    pensando = True
                    startAudioThread()  # inicia o processo de pensamento
                    # phrase_time_limit: máximo de segundos que isso permitirá que uma frase continue antes de parar e retornar a parte da frase processada
                try:
                    # Transforma o audio escutado em texto
                    textoFalado = recognizer.recognize_google(audioEscutado, language="pt-BR") # utiliza o google para detectar o texto
                    
                except speech_recognition.UnknownValueError as erro:
                    if(str(erro) != ""):
                        print("\033[32m[LOG]\033[0;0m \033[32m[ERR]\033[0;0m: "+str(erro))
                pensando = False

                    
        elif motor_reconhecimento == "vosk":
            # Reconhecer do mic
            stream = pyAudio.open(format = pyaudio.paInt16, channels = 1, rate = 16000, input = True, frames_per_buffer = 8192)
            stream.start_stream()
            while textoFalado == "":
                data = stream.read(10240)
                if voskRecognizer.AcceptWaveform(data):
                    textoFalado = json.loads(voskRecognizer.Result())['text']

    print(" \033[32m[LOG]\033[0;0m Eu escutei: "+textoFalado)   
    return textoFalado.lower()

"""
Checa o texto por meio das condições para tentar entender o que foi falado. Se enteder algo, dá uma resposta em audio
"""
def main():
    global motor_reconhecimento
    global recognizer

    thread = Thread(target=verificarFalaNoFirebase, args=())
    thread.daemon = True  # https://stackoverflow.com/questions/11815947/cannot-kill-python-script-with-ctrl-c
    thread.start()

    while True:
        # variável usada quando alguém pede para falar algo no sistema web
        global falandoViaFirebase
        # variável usada quando alguém interage pelo sistema web
        global escutarDoFirebase

        # só executa quando tem certeza que não está acontecendo uma interação pelo firebase
        if falandoViaFirebase == False:
            global expressoesConecta
            if expressoesConecta.estado != "ausente":
                setarExpressao("ausente")
            global keyword_index
 
            # processa o áudio com porcupine
            pcm = audio_stream.read(porcupine.frame_length, exception_on_overflow = False)
            # processa o áudio com porcupine
            pcm = struct.unpack_from("h" * porcupine.frame_length, pcm) 
            # armazena o resultado
            keyword_index = porcupine.process(pcm)

            #ativa o robô pelo sistema web, ignorando a palavra de ativação
            if escutarDoFirebase == True or ignorarPicovoice == True: 
                keyword_index = 1

            # se a palavra for falada, a condição retorna true
            if keyword_index >= 0:   
                respostas = []
                global parar
                parar = False
                global numeroRespostas
                numeroRespostas = 0
                playsound("audios/awake.mp3")
                
                while not parar:# or time.time() - inicioDelay < 60)): # Enquanto não tiver passado no mínimo 1 minutos dentro do while ele continua aguardando uma pergunta
                    global pensando
                    hora = datetime.today().hour
                    setarExpressao("aguardando")
                    textoFalado = escutarMicrofone()

                    # inicia a função que procura por palavras proibidas nas frase utilizando outra classe python
                    analise = AnalisePalavras()

                    # verifica cada palavra falada
                    for i in textoFalado.split():
                        retorno = analise.avalia(str(i))
                        if (retorno['score'] == 1):
                            print(" \033[31m[ERR] Palavra censurada! a palavra " + i + " não é permitida! \033[0;0m")
                            respostas = ["Desculpe, detectei uma palavra imprópria, não estou autorizado a responder."]
                            numeroRespostas = numeroRespostas + 1
                        


                    # Verifica se a pergunta já foi respondida no firebase
                    if motor_reconhecimento != "vosk":
                        perguntas = db.reference("Perguntas").get()
                        for i in perguntas:
                            if i.replace("?","") in textoFalado:
                                print(" \033[32m[LOG]\033[0;0m Registro encontrado no Firebase.")
                                try:
                                    resposta = db.reference("Perguntas").child(i).get()["resposta"]
                                    
                                    if resposta != ["n/a"]:                                 
                                        respostas = resposta
                                        numeroRespostas = numeroRespostas + 1
                                        
                                except Exception as e:
                                    print(" \033[31m[ERR] ERRO CRÍTICO! "+e+"\033[0;0m")
                                    respostas = ["não consegui conectar com o banco de respostas, tente mais tarde"]
                                    print
                                    numeroRespostas = numeroRespostas + 1


                    # esse comando faz o robô recalibrar o microfone, mas ele não demonstrará que está fazendo isso
                    if "calibrar microfone em silêncio" in textoFalado and numeroRespostas==0:
                        numeroRespostas = numeroRespostas + 1
                        ajustarRuidos()

                    # esse comando faz o robô recalibrar o microfone falando que está recalibrando e pedindo para esperar
                    if "calibrar microfone" in textoFalado and numeroRespostas==0:
                        numeroRespostas = numeroRespostas + 1
                        ajustarRuidos(True)

                    # esse comando faz falar o ultimo comando escutado
                    if ("que você ouviu" in textoFalado or "que você escutou" in textoFalado) and numeroRespostas==0:
                        numeroRespostas = numeroRespostas + 1
                        if escutado != None:
                            respostas = ["Eu ouvi: " + escutado]
                        else:
                            respostas = ["Ainda não ouvi nada"]

                    # comando responsável por cadastrar rosto ou falar quem está sendo reconhecido
                    if ("quem eu sou" in textoFalado or "quem sou eu" in textoFalado) and numeroRespostas==0:
                        numeroRespostas = numeroRespostas + 1
                        # só prossegue se detectar um rosto
                        if ConectaVision.faceDetectada == True:
                            # se não reconhecer, pergunta se quer se cadastrar
                            if ConectaVision.nomeRostoReconhecido == "Desconhecido":
                                falar(["Não sei quem você é, mas posso aprender a te reconhecer. Você quer que eu aprenda?"])
                                setarExpressao("aguardando")
                                playsound("audios/awake.mp3")
                                respostaReconhecimento = escutarMicrofone()
                                if "sim" in respostaReconhecimento:
                                    falar(["Por favor, informe seu nome. é por ele que vou aprender a te reconhecer"])
                                    setarExpressao("aguardando")
                                    playsound("audios/awake.mp3")
                                    respostaReconhecimento = escutarMicrofone()
                                    ConectaVision.nomeRosto = respostaReconhecimento
                                    falar(["Ótimo, por favor posicione-se na frente da câmera e aguarde as instruções"])
                                    playsound("audios/thinking.mp3")
                                    playsound("audios/thinking.mp3")
                                    if ConectaVision.faceDetectada == False:
                                        falar(["Não consegui detectar o seu rosto, certifique-se de aparecer bem na câmera. as condições de iluminação podem interferir no meu sistema de rastreamento de objetos ou pessoas"])
                                    elif  ConectaVision.faceDetectada == True:
                                        falar(["Ótimo, estou rastreando os seus dados faciais para aprender a reconhecê-los, aguarde"])
                                        playsound("audios/thinking.mp3")
                                        if ConectaVision.cadastrarRosto() == False:
                                            falar(["Não consegui rastrear seus dados faciais, verifique se você está sendo detectado na câmera e se está bem iluminado. Após isso você pode tentar esse processo novamente"])
                                        else:
                                            respostas = ["Pronto " + ConectaVision.nomeRosto + "! agora eu sem quem você é."]
                            
                                elif "não" in respostaReconhecimento:
                                    respostas = ["Certo, então tudo bem. Até logo"]
                                else:
                                    respostas = ["Desculpe, eu não entendi. Você pode tentar falar novamente depois"]
                            else:
                                respostas = ["Olá, " + ConectaVision.nomeRostoReconhecido + "! É claro que eu sei", "Sim, você é o " + ConectaVision.nomeRostoReconhecido + "! ", "Você é o " + ConectaVision.nomeRostoReconhecido + "!"]
                        else: 
                            respostas = ["Não estou enxergando bem no momento, tente novamente."]

                    # altera a skin para advogado
                    if ("vire um advogado" in textoFalado or "modo advogado" in textoFalado) and numeroRespostas==0:
                        numeroRespostas = numeroRespostas + 1
                        expressoesConecta.alterarSkin("advogado")
                        setarExpressao("respondendo")
                        respostas = ["Ok, agora eu sou um advogado!"]
                    # altera a skin para psicólogo
                    if ("vire um psicólogo" in textoFalado or "modo psicólogo" in textoFalado) and numeroRespostas==0:
                        numeroRespostas = numeroRespostas + 1
                        expressoesConecta.alterarSkin("psicologo")
                        setarExpressao("respondendo")
                        respostas = ["Ok, agora eu sou um psicólogo!"]
                    # altera a skin para a padrão
                    if "use a roupa padrão" in textoFalado and numeroRespostas==0:
                        numeroRespostas = numeroRespostas + 1
                        expressoesConecta.alterarSkin("citec")
                        setarExpressao("respondendo")
                        respostas = ["Ok, agora estou com a camisa do centro de inovação tecnológica!", "Ok, agora eu estou com a mesma roupa que meus amigos do centro de inovação!"]
                            
                    if "olá" in textoFalado and numeroRespostas==0:
                        numeroRespostas = numeroRespostas + 1
                        falar(["Olá, tudo bem com você?"])
                        setarExpressao("aguardando")
                        playsound("audios/awake.mp3")
                        respostaBoasVindas = escutarMicrofone()
                        if "não" in respostaBoasVindas:
                            setarExpressao("triste")
                            respostas = ["Que pena. Desejo que esteja melhor o mais breve possível"]
                        elif "sim" in respostaBoasVindas:
                            setarExpressao("respondendo")
                            respostas = ["Que ótimo! Também estou bem. Melhor agora."]
                        else :
                            respostas = ["ops, não entendi, mas espero que seu dia esteja ótimo"]


                    if "bom dia" in textoFalado and numeroRespostas==0:
                                numeroRespostas = numeroRespostas + 1
                                if hora < 12 and hora >= 4:
                                    respostas = ["Bom dia! Espero que seu dia seja ótimo"]
                                else:
                                    if hora < 17 and hora >= 12:
                                        respostas = ["Bom dí. Boa tarde! Seu relógio parece estar atrasado", "Bom dí. Boa tarde! Seu relógio pode estar atrasado"]
                                    if hora >= 17 or hora < 4:
                                        respostas = ["Bom dí. Boa noite! Seu relógio pode estar atrasado", "Bom dí. Boa noite! Seu relógio parece estar atrasado"]
                    
                    if "boa tarde" in textoFalado and numeroRespostas==0:
                                numeroRespostas = numeroRespostas + 1
                                if hora < 17 and hora >= 12:
                                    respostas = ["Boa tarde! Espero que seu dia esteja ótimo"]
                                else:
                                    if hora >= 17 or hora < 4:
                                        respostas = ["Boa tá. Boa noite! creio que seu relógio está atrasado.", "Boa tá. Boa noite! verifique se o seu relógio não está atrasado."]
                                    if hora < 12 and hora >= 4:
                                        respostas = ["Boa tá. Bom dia! creio que seu relógio está adiantado.", "Boa tá. Bom dia! verifique se o seu relógio não está adiantado."]
                        
                    if "boa noite" in textoFalado and numeroRespostas==0:
                                numeroRespostas = numeroRespostas + 1
                                if hora >= 17 or hora < 4:
                                    respostas = ["Boa noite! Espero que seu dia tenha sido ótimo"]
                                else:
                                    if hora < 17 and hora >= 12:
                                        respostas = ["Boa noí. Boa tarde! creio que seu relógio está errado.", "Boa noí. Boa tarde! verifique se o seu relógio não está adiantado."]
                                    if hora < 12 and hora >= 4:
                                        respostas = ["Boa noí. Bom dia! seu relógio pode estar errado.", "Boa noí. Bom dia! creio que seu relógio está adiantado."]
    

                    # if 'conecta' in textoFalado or 'totem' in textoFalado and numeroRespostas==0:
                    #     numeroRespostas = numeroRespostas + 1
                    #     if inteligencia == "conecta":
                    #         setarExpressao("respondendo")
                    #         respostas = ["sim, já estou ouvindo"]
                    #     else:
                    #         setarExpressao("respondendo")
                    #         respostas = ["sim, já estou ouvindo"]

                    
                    # if ("listar comandos" in textoFalado or "exibir comandos" in textoFalado or "lista comandos" in textoFalado) and numeroRespostas==0:
                    #     expressoesConecta.mostraTela = False
                    #     setarExpressao("respondendo")
                    #     numeroRespostas = numeroRespostas + 1
                    #     print("\033[32mSAUDAÇÕES\033[0;0m: ------------------------------------------------- olá | bom dia | boa tarde | boa noite")
                    #     print("\033[32mHORÁRIO\033[0;0m: --------------------------------------------------- que horas são?")
                    #     print("\033[32mELOGIO\033[0;0m: ---------------------------------------------------- você é inteligente")
                    #     print("\033[32mDESCULPAR-SE\033[0;0m: ---------------------------------------------- desculpa | me desculpa")
                    #     print("\033[32mVER COMANDOS\033[0;0m: ---------------------------------------------- listar comandos")
                    #     print("\033[32mDESPEDIR-SE\033[0;0m: ----------------------------------------------- até mais | até logo | tchau | até a próxima")
                    #     if inteligencia=="totem":
                    #         print("\033[32mCHAMAR\033[0;0m: ---------------------------------------------------- ei totem")
                    #     else:
                    #         print("\033[32mCHAMAR\033[0;0m: ---------------------------------------------------- conecta")
                    #     print("                               ")
                    #     print('\033[32mFALAR "ocultar terminal" OU "\033[33mesconder terminal\033[32m" OU "\033[33mmostrar? rosto\033[32m" OU "\033[33mexibir rosto\033[32m" PARA EXIBIR A INTERFACE...\033[0;0m')
                    #     respostas = ['Aqui está uma lista com os meus comandos, você pode ocultar esta tela falando "ocultar terminal"!']
                        

                    if "horas são" in textoFalado and numeroRespostas==0:
                        numeroRespostas = numeroRespostas + 1
                        setarExpressao("respondendo")
                        respostas = ["Agora são "+str(datetime.today().hour)+" horas e "+str(datetime.today().minute)+" minutos"]
                    
                    if "conversa" in textoFalado and numeroRespostas==0:
                        setarExpressao("respondendo")
                        respostas = ["Converso sim. Você pode me perguntar o que é o núcleo de robótica, quem eu sou e até mesmo me pedir para contar uma piada."]
                    
                    if "obrigad" in textoFalado and numeroRespostas==0:
                        numeroRespostas = numeroRespostas + 1
                        setarExpressao("respondendo")
                        respostas = ["Foi um prazer te responder", "Tamo junto", "Não há de quê", "De nada"]
                    
                    if "desculpa" in textoFalado and numeroRespostas==0:
                        numeroRespostas = numeroRespostas + 1
                        setarExpressao("respondendo")
                        respostas = ["Tá tudo bem", "Sem problemas"]
                        
                    if "até mais" in textoFalado or "até logo" in textoFalado or "tchau" in textoFalado or "até a próxima" in textoFalado and numeroRespostas==0:
                        setarExpressao("respondendo")
                        numeroRespostas = numeroRespostas + 1
                        respostas = ["Tchau, adorei ter falado com você", "Até mais", "Tchauzinho"]
                    
                    
                    # Se não tiver entendido o que foi falado (isso roda apenas se a conecta ainda não tiver dado nenhuma resposta)
                    if(len(respostas) == 0 and numeroRespostas == 0):

                        # Grava o "não entendi" como resposta  (só será falado sem o módulo OPENAI)
                        respostas = ["Desculpa, não entendi o que você falou"]

                        # Verifica se a engine de reconhecimento de voz é o vosk (isso também serve para verificar se a internet será usada)
                        if motor_reconhecimento != "vosk":
                            # Verifica se algo foi falado
                            if textoFalado:

                                if len(textoFalado)<757: #Limite que um id pode ter no firebase (evita que tente gravar uma pergunta muito grande)
                                    try:
                                        setarExpressao("respondendo")
                                        falar(["Aguarde, estou pensando", "Aguarde enquanto pesquiso", "Por favor aguarde, estou pesquisando"])
                                        setarExpressao("aguardando")
                                        # Define que o som de pensar irá ser executado até a variável voltar a ser false
                                        pensando = True
                                        startAudioThread()
                                        pergunta = None
                                        try:
                                            # Busca a pergunta realizada no firebase
                                            pergunta = db.reference("Perguntas").child(textoFalado).get()

                                            # Verifica se a pergunta existe
                                            if pergunta:
                                                # Se existir, busca a resposta da pergunta
                                                resposta = db.reference("Perguntas").child(textoFalado).get()["resposta"]
                                        except Exception as e:
                                            print(" \033[31m[ERR] Erro, não foi possível conectar com o firebase.\033[0;0m")

                                        # Verifica se a pergunta ou a resposta não existem
                                        if pergunta == None or resposta == ["n/a"]:
                                            # Se não existir, printa que não encontrou resposta (opcional)
                                            print(" \033[31m[ERR] Nenhuma resposta encontrada.\033[0;0m")
                                            # Printa busca no openai (opcional)
                                            print(" \033[96m[OPENAI]\033[0;0m Conectando-se a https://platform.openai.com...")
                                            print(" \033[96m[OPENAI]\033[0;0m Modelo: text-davinci-003")
                                            # Salva a pergunta no firebase para que possa seer usada futuramente
                                            try:
                                                db.reference("Perguntas").child(textoFalado).set({"pergunta": textoFalado, "resposta": ["n/a"]})
                                            except Exception as e:
                                                print(" \033[31m[ERR] Erro, não foi possível conectar com o firebase.\033[0;0m")
                                            #pega a chave de API da open ai
                                            
                                            openai.api_key = os.getenv('OPENAI_TOKEN') 
                                            
                                            skin = db.reference("Conecta").get()["skin"]
                                            
                                            if skin == "citec":
                                                prompt = "Você receberá uma mensagem de um usuário que estará delimitada pela tag <mensagem></mensagem>.  Seu nome será Totem, você é uma inteligência artificial desenvolvida pelo centro de inovação tecnológica do cesmac. Você não precisa se apresentar. <mensagem>"
                                                prompt =  prompt + textoFalado + "</mensagem>"
                                            else:
                                                prompt = "Você receberá uma mensagem de um usuário que estará delimitada pela tag <mensagem></mensagem>.  Seu nome será Totem, você é uma inteligência artificial desenvolvida pelo centro de inovação tecnológica do cesmac. Você não precisa se apresentar. Sua especialidade é ser um "+skin+". <mensagem>"
                                                prompt =  prompt + textoFalado + "</mensagem>"

                                            
                                            # Utiliza o serviço da OPEN AI - https://platform.openai.com/docs/api-reference/completions/create?lang=python
                                            response = openai.Completion.create(
                                                engine="text-davinci-003", # Modelo a ser utilizado
                                                prompt=prompt, # Texto a ser passado para processar
                                                temperature=0.5, # Valores mais altos significam que o modelo assumirá mais riscos
                                                max_tokens=256, # A contagem de token de seu prompt plus max_tokensnão pode exceder o comprimento do contexto do modelo. A maioria dos modelos tem um comprimento de contexto de 2.048 tokens (exceto os modelos mais novos, que suportam 4.096). - https://platform.openai.com/tokenizer
                                                top_p=1.0, # Uma alternativa para amostragem com temperature
                                                frequency_penalty=0.0, # Número entre -2,0 e 2,0. Valores positivos penalizam novos tokens com base em sua frequência existente no texto até o momento, diminuindo a probabilidade do modelo repetir a mesma linha textualmente.
                                                presence_penalty=0.0 # Número entre -2,0 e 2,0. Valores positivos penalizam novos tokens com base em sua presença no texto até o momento, aumentando a probabilidade do modelo falar sobre novos tópicos.
                                            )

                                            pensando = False # Define que o som de pensar irá parar de ser executado

                                            # Muda a expressão
                                            setarExpressao("respondendo")
                                            
                                            # Fala a resposta retornada pela open ai
                                            falar([response['choices'][0]['text']])
                                        else: 
                                            pensando = False # Define que o som de pensar irá parar de ser executado

                                            # Muda a expressão
                                            setarExpressao("respondendo")
                                            # Fala a resposta retornada pelo firebase
                                            falar(respostas)
                                        # Determina que pare de escutar após esta execução
                                        parar = True
                                        playsound("audios/sleep.mp3")

                                    except Exception as e:
                                        parar = True
                                        pensando = False # Define que o som de pensar irá parar de ser executado
                                        print(" \033[31m[ERR] Ocorreu um erro ao conectar - "+str(e)+".\033[0;0m")
                                        setarExpressao("triste")
                                        falar(["Desculpe não consegui me conectar com os servidores. Espero conseguir responder você assim que possível."])
                                        
                                        playsound("audios/sleep.mp3")
                        else:
                            setarExpressao("respondendo")
                            
                            # Fala que não entendeu
                            falar(respostas)
                            
                    else:
                        # soma uma resposta no registro
                        numeroRespostas = numeroRespostas + 1
                    if respostas != ["Desculpa, não entendi o que você falou"]:
                        # Fala a resposta fornecida pelos if's else's
                        if len(respostas) > 0:
                            setarExpressao("respondendo")
                            falar(respostas)
                        parar = True
                        playsound("audios/sleep.mp3")
                        
                    # Reseta a quantidade de respostas
                    escutado = textoFalado
                    respostas = []
                    numeroRespostas = 0
            
"""
Altera a expressão do visor
"""
def setarExpressao(nomeExpressao):
    global expressoesConecta
    expressoesConecta.alterarEstado(nomeExpressao)

"""
Ajusta o ruído do ambiente para não reconhecer barulhos como fala
"""
def ajustarRuidos(reajustar = False):
    if reajustar == True:
        setarExpressao("respondendo")
        falar(["Recalibrando microfone, aguarde um momento."])
        setarExpressao("aguardando")
    print(" \033[32m[LOG]\033[0;0m Calibrando o microfone...")
    with speech_recognition.Microphone() as origemAudio:
        # Calibra baseado em 5 segundos de som ambiente (fazer silêncio quando isso for executado, apenas o som do ambiente deve ser processado)
        recognizer.adjust_for_ambient_noise(origemAudio, duration=5)
        print(" \033[32m[LOG]\033[0;0m Inicializando Speech Recognition...")
        print(" \033[33m[WARN]\033[0;0m Fale algo para inicializar mais rápido...")
        startAudioVerificador()
        # escuta áudio por 1 segundo para inicializar
        audioEscutado = recognizer.listen(origemAudio, phrase_time_limit=1.0)
        if reajustar == True:
            setarExpressao("respondendo")
            falar(["O microfone foi recalibrado para o ambiente atual"])
            setarExpressao("aguardando")
    try:
        # Transforma o audio escutado em texto
        print(" \033[32m[LOG]\033[0;0m Conectando ao serviço de reconhecimento de fala...")
        recognizer.recognize_google(audioEscutado, language="pt-BR")
        
        
    except speech_recognition.UnknownValueError as erro:
        if(str(erro) != ""):
            print("[LOG] Erro: "+str(erro))

"""
Verifica a conexão com à internet
"""
def checa_internet():
    url = 'https://www.google.com' # utiliza o google como base
    timeout = 5 # Tempo máximo pra carregar

    try:
        requests.get(url, timeout=timeout) # Testa a conexão
        return True # retorna sucesso
    except:
        return False # retorna falha



"""
# # # # # # # # # # # # # # # # Inicialização da Conecta # # # # # # # # # # # # # # # # # # # 
"""

# seta o terminal em tela cheia
keyboard.press('f11')

boot(inteligencia)
    
# Inicialização do firebase
credencial = credentials.Certificate("serviceAccountKey.json")
firebase = firebase_admin.initialize_app(credencial, {
    'databaseURL': 'https://autcitec-default-rtdb.firebaseio.com/'
})

credencialAlunos = credentials.Certificate("serviceAccountKey_alunos.json")
firebaseAlunos = firebase_admin.initialize_app(credential = credencialAlunos, name = "alunos",
    options = {'databaseURL': 'https://porta-citec-alunos-default-rtdb.firebaseio.com/'})

# Inicializar PyAudio - Utilizado pelo porcupine e vosk
pyAudio = pyaudio.PyAudio()

# Inicializar o porcupine - Utilizado para a wake word
porcupine = pvporcupine.create(
            sensitivities=[0.5], # sensibilidade de ativação - maior=melhor escuta - float de 0 a 1
            access_key=os.getenv('PICOVOICE_ACCESS_KEY'), 
            keyword_paths=keyword_paths, 
            model_path=model_path)

# inicializar microfone para o porcupine
audio_stream = pyAudio.open(
            rate=porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=porcupine.frame_length)

print(" \033[32m[LOG]\033[0;0m Verificando conexão com à internet. Por favor, aguarde!...")

if(checa_internet()==True):
    print(" \033[32m[LOG]\033[0;0m Conectado ao serviço de reconhecimento de voz do google.")
    motor_reconhecimento = "speechrecognition"
else:
    
    print(" \033[31m[ERR] ERRO CRÍTICO! Falha ao conectar-se, o reconhecimento de voz foi alterado para o modo offline.\033[0;0m")
    motor_reconhecimento = 'vosk'

    ReproducaoVideo.offline = True
    falar(["Falha de conexão. Alterando para o modo offline. O reconhecimento de voz ficará impreciso."])
    

if motor_reconhecimento == "vosk":
    # # Inicializar o Vosk - Um dos reconhecimentos de voz para as perguntas
    voskModel = Model('vosk-model-small-pt-0.3')
    voskRecognizer = KaldiRecognizer(voskModel, 16000)
    # voskRecognizer.SetWords(True)

if motor_reconhecimento == "speechrecognition":
    # Inicializar o speech recognition
    recognizer = speech_recognition.Recognizer()
    # recognizer.set_threshold = 500
    recognizer.dynamic_energy_threshold = False
    recognizer.energy_threshold = 0   # menor = escuta mais longe | maior = escuta menos - ideal: 50 a 4000
    ajustarRuidos()

print(" \033[32m[LOG]\033[0;0m Iniciando Expressões...")


expressoesConecta = ReproducaoVideo('ausente')


main()