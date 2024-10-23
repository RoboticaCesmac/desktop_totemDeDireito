from random import randint
from datetime import datetime
from ReproducaoVideo import ReproducaoVideo
from elevenlabs import generate, play, set_api_key
from threading import Thread 
from boot import boot
import struct
import os
import requests
import time

import datetime as dt
# BIBLIOTECAS INSTALADAS POR FORA
from analise_palavras import AnalisePalavras
from playsound import playsound
from firebase_admin import credentials
from firebase_admin import db
from dotenv import load_dotenv
import firebase_admin
import speech_recognition
import keyboard
from openai import OpenAI
import ConectaVision

# Inicialização do firebase
credencial = credentials.Certificate("serviceAccountKey.json")
firebase = firebase_admin.initialize_app(credencial, {
    'databaseURL': 'https://autcitec-default-rtdb.firebaseio.com/'
})


escutado = None # Registra o que foi falado na ultima interação
inteligencia = "totem" # Define qual é a I.A que irá assumir o controle - conecta ou totem
load_dotenv() # Carrega o plug-in do dotenv
set_api_key(os.getenv('ELEVENLABS_API_KEY')) # Carrega a api key do elevenlabs
threadSom = False # Thread de diálogo pela rede firebase
parar = False # False = não escuta - True = escutando
numeroRespostas = 0 # Determina quando a I.A não entende
keyword_index = 0 #quando maior que 0, é por que o detectou a palavra de ativação
estaFalando = False # define quando o robô está falando
falandoViaFirebase = False # Quando verdadeiro, faz com que o robô fale uma frase gravada no firebase via app
escutarDoFirebase = False # Quando verdadeiro, permite que interaja com o robô por texto a partir do Firebase, ignorando o reconhecimento de voz
pensando = False
modelo = ""

"""
É uma função que verifica vários estados do firebase que podem ser usados para ativar gatilhos no código
"""
def verificarFirebase():
    global falandoViaFirebase, escutarDoFirebase
    while True:
        # verifica se a cor do olho foi alterada no firebase e seta ela na classe do visor
        ReproducaoVideo.alterarCorDoOlho(db.reference(inteligencia.capitalize()).child("corDoOlho").get())
        
        # verifica se foi solicitado que o totem fale algo pelo firebase
        executarViaFirebase = db.reference(inteligencia.capitalize()).child("executar").child("executar").get()
        falaViaFirebase = db.reference(inteligencia.capitalize()).child("fala").child("falar").get()
        escutarDoFirebase = db.reference(inteligencia.capitalize()).child("escuta").child("escutar").get()
        print(escutarDoFirebase)

        if falaViaFirebase == True:
            interacao = db.reference(inteligencia.capitalize()).child("fala").child("texto").get()
            falandoViaFirebase = True
            setarExpressao("respondendo")
            playsound("audios/awake.mp3")
            # Se existir, busca a resposta da pergunta
            falar([interacao])
            playsound("audios/sleep.mp3")
            falandoViaFirebase = False
            db.reference(inteligencia.capitalize()).child("fala").child("falar").set(False)
            db.reference(inteligencia.capitalize()).child("fala").child("texto").set("")
                   
        if executarViaFirebase == True:
            interacao = db.reference(inteligencia.capitalize()).child("executar").child("interacao").get()
            falandoViaFirebase = True
            if db.reference("Perguntas").child(interacao).get()["tipo"] == "resposta":
                setarExpressao("respondendo")
                playsound("audios/awake.mp3")
                # Se existir, busca a resposta da pergunta
                falar(db.reference("Perguntas").child(interacao).get()["resposta"])
                playsound("audios/sleep.mp3")
                falandoViaFirebase = False
            else:
                codigo = db.reference("Perguntas").child(interacao).get()["codigo"]
                try:
                    exec(codigo)
                except Exception as e:
                    print(" \033[31m[ERR]\033[0;0m Erro, "+str(e)+".\033[0;0m")
            
            db.reference(inteligencia.capitalize()).child("executar").child("executar").set(False)
            db.reference(inteligencia.capitalize()).child("executar").child("interacao").set("")
        


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
        # Verifica se é pra usar o ElevenLabs
        if(db.reference(inteligencia.capitalize()).child("fala").child("useElevenlabs").get() == True):
            try:
                audio = generate(text=texto, voice=db.reference(inteligencia.capitalize()).child("fala").child("vozElevenlabs").get(), model='eleven_multilingual_v2')
                setarExpressao("respondendo")
                play(audio)
            except Exception as e:
                print(" \033[32m[LOG]\033[0;0m \033[32m[ERR]\033[0;0m erro no Elevenlabs: " + str(e))
                setarExpressao("respondendo")
                from sintetizador import _TTS
                tts = _TTS(inteligencia)
                tts.start(texto)
                del(tts)
        else:
            setarExpressao("respondendo")
            from sintetizador import _TTS
            tts = _TTS()
            tts.start(texto)
            del(tts)
        setarExpressao("ausente")
        print(" \033[32m[LOG]\033[0;0m Eu falei: "+texto)


"""
Fica escutando o microfone e chama a função de entender o que foi falado quando é reconhecido algum som
"""
def escutarMicrofone():
    global parar, escutarDoFirebase, pyAudio, pensando
    try:
        textoFalado = ""
        

        # ignora a escuta do microfone se for solicitado uma interação pelo sistema web/firebase
        if escutarDoFirebase == True:
            print("FIREBASE Ó")
            textoFalado = "totem"+db.reference(inteligencia.capitalize()).child("escuta").child("texto").get()
            db.reference(inteligencia.capitalize()).child("escuta").child("escutar").set(False)
            db.reference(inteligencia.capitalize()).child("escuta").child("texto").set("")
            escutarDoFirebase = False
        # escuta o microfone
        else:
            presentDate = dt.datetime.now() # pega a data atual 
            unix_timestamp = dt.datetime.timestamp(presentDate)*1000 # transforma a data em unix timestamp
            unix_timestamp = int(str(int(unix_timestamp))[:-3]) # formata o unix para retirar milésimos
            
            while textoFalado == "": 
                presentDate = dt.datetime.now() # pega a data atual
                if int(str(int(dt.datetime.timestamp(presentDate)*1000))[:-3]) - 15 > unix_timestamp: #compara a data atual com a anterior em unix time e para a execução caso passe 15 segundos sem entender nada
                    parar = True # Para de escutar e dorme
                    numeroRespostas = numeroRespostas + 1 # Impede que peça desculpas por não ter entendido
                    print(" \033[33m[WARN]\033[0;0m Microfone desligado por inatividade")
                    break

                with speech_recognition.Microphone() as origemAudio:
                    print(" \033[32m[LOG]\033[0;0m Escutando microfone...")
                    audioEscutado = recognizer.listen(origemAudio)#, phrase_time_limit=5.0) # escuta o microfone
                    pensando = True
                    # startAudioThread()  # inicia o processo de pensamento
                    # phrase_time_limit: máximo de segundos que isso permitirá que uma frase continue antes de parar e retornar a parte da frase processada
                try:
                    # Transforma o audio escutado em texto
                    textoFalado = recognizer.recognize_google(audioEscutado, language="pt-BR") # utiliza o google para detectar o texto
                    
                except speech_recognition.UnknownValueError as erro:
                    if(str(erro) != ""):
                        print("\033[32m[LOG]\033[0;0m \033[32m[ERR]\033[0;0m: "+str(erro))
                pensando = False

        print(" \033[32m[LOG]\033[0;0m Eu escutei: "+textoFalado)   
        return textoFalado
    except Exception as e:
        print("\033[32m\033[0;0m \033[32m[ERR]\033[0;0m: "+str(e))
        return " "

"""
Checa o texto por meio das condições para tentar entender o que foi falado. Se enteder algo, dá uma resposta em audio
"""
def main():
    global falandoViaFirebase, escutarDoFirebase, expressoesConecta, keyword_index, parar, numeroRespostas, pensando, textoFalado

    thread = Thread(target=verificarFirebase, args=())
    thread.daemon = True  # https://stackoverflow.com/questions/11815947/cannot-kill-python-script-with-ctrl-c
    thread.start()

    while True:
        # só executa quando tem certeza que não está acontecendo uma interação pelo firebase
        if falandoViaFirebase == False:
            if expressoesConecta.estado != "ausente":
                setarExpressao("ausente")

            respostas = []
            parar = False
            numeroRespostas = 0

            while not parar:# or time.time() - inicioDelay < 60)): # Enquanto não tiver passado no mínimo 1 minutos dentro do while ele continua aguardando uma pergunta
                hora = datetime.today().hour
                textoFalado = escutarMicrofone()

                if inteligencia in textoFalado or expressoesConecta.estado == "aguardando":
                    if inteligencia in textoFalado and len(textoFalado.split(inteligencia)) > 1:
                        textoFalado = textoFalado.split(inteligencia)[1]
                    if textoFalado == "" or textoFalado == " ":
                        break

                    # inicia a função que procura por palavras proibidas nas frase utilizando outra classe python
                    analise = AnalisePalavras()

                    # verifica cada palavra falada
                    for i in textoFalado.split():
                        retorno = analise.avalia(str(i))
                        if (retorno['score'] == 1):
                            print(" \033[31m[ERR] Palavra censurada! a palavra " + i + " não é permitida! \033[0;0m")
                            respostas = ["Desculpe, detectei uma palavra imprópria, não estou autorizado a responder."]
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
                    # if ("quem eu sou" in textoFalado or "quem sou eu" in textoFalado) and numeroRespostas==0:
                    #     numeroRespostas = numeroRespostas + 1
                    #     # só prossegue se detectar um rosto
                    #     if ConectaVision.faceDetectada == True:
                    #         # se não reconhecer, pergunta se quer se cadastrar
                    #         if ConectaVision.nomeRostoReconhecido == "Desconhecido":
                    #             falar(["Não sei quem você é, mas posso aprender a te reconhecer. Você quer que eu aprenda?"])
                    #             setarExpressao("aguardando")
                    #             playsound("audios/awake.mp3")
                    #             respostaReconhecimento = escutarMicrofone()
                    #             if "sim" in respostaReconhecimento:
                    #                 falar(["Por favor, informe seu nome. é por ele que vou aprender a te reconhecer"])
                    #                 setarExpressao("aguardando")
                    #                 playsound("audios/awake.mp3")
                    #                 respostaReconhecimento = escutarMicrofone()
                    #                 ConectaVision.nomeRosto = respostaReconhecimento
                    #                 falar(["Ótimo, por favor posicione-se na frente da câmera e aguarde as instruções"])
                    #                 playsound("audios/thinking.mp3")
                    #                 playsound("audios/thinking.mp3")
                    #                 if ConectaVision.faceDetectada == False:
                    #                     falar(["Não consegui detectar o seu rosto, certifique-se de aparecer bem na câmera. as condições de iluminação podem interferir no meu sistema de rastreamento de objetos ou pessoas"])
                    #                 elif  ConectaVision.faceDetectada == True:
                    #                     falar(["Ótimo, estou rastreando os seus dados faciais para aprender a reconhecê-los, aguarde"])
                    #                     playsound("audios/thinking.mp3")
                    #                     if ConectaVision.cadastrarRosto() == False:
                    #                         falar(["Não consegui rastrear seus dados faciais, verifique se você está sendo detectado na câmera e se está bem iluminado. Após isso você pode tentar esse processo novamente"])
                    #                     else:
                    #                         respostas = ["Pronto " + ConectaVision.nomeRosto + "! agora eu sem quem você é."]
                            
                    #             elif "não" in respostaReconhecimento:
                    #                 respostas = ["Certo, então tudo bem. Até logo"]
                    #             else:
                    #                 respostas = ["Desculpe, eu não entendi. Você pode tentar falar novamente depois"]
                    #         else:
                    #             respostas = ["Olá, " + ConectaVision.nomeRostoReconhecido + "! É claro que eu sei", "Sim, você é " + ConectaVision.nomeRostoReconhecido + "! ", "Você é " + ConectaVision.nomeRostoReconhecido + "!"]
                    #     else: 
                    #         respostas = ["Não estou enxergando bem no momento, tente novamente."]

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
                    if ("vire um personal" in textoFalado or "modo personal" in textoFalado) and numeroRespostas==0:
                        numeroRespostas = numeroRespostas + 1
                        expressoesConecta.alterarSkin("personal trainer")
                        setarExpressao("respondendo")
                        respostas = ["Ok, agora eu sou um personal trainer!"]
                    # altera a skin para a padrão
                    if "use a roupa padrão" in textoFalado and numeroRespostas==0:
                        numeroRespostas = numeroRespostas + 1
                        expressoesConecta.alterarSkin("citec")
                        setarExpressao("respondendo")
                        respostas = ["Ok, agora estou com a camisa do centro de inovação tecnológica!", "Ok, agora eu estou com a mesma roupa que meus amigos do centro de inovação!"]
                            


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

                    if "horas são" in textoFalado and numeroRespostas==0:
                        numeroRespostas = numeroRespostas + 1
                        setarExpressao("respondendo")
                        respostas = ["Agora são "+str(datetime.today().hour)+" horas e "+str(datetime.today().minute)+" minutos"]
                        
                    if "até mais" in textoFalado or "até logo" in textoFalado or "tchau" in textoFalado or "até a próxima" in textoFalado and numeroRespostas==0:
                        setarExpressao("respondendo")
                        numeroRespostas = numeroRespostas + 1
                        respostas = ["Tchau, adorei ter falado com você", "Até mais", "Tchauzinho"]
                    
                    # Se não tiver entendido o que foi falado (isso roda apenas se a conecta ainda não tiver dado nenhuma resposta)
                    if(len(respostas) == 0 and numeroRespostas == 0):

                        # Grava o "não entendi" como resposta  (só será falado sem o módulo OPENAI)
                        respostas = ["Desculpa, não entendi o que você falou"]
                        # Verifica se algo foi falado
                        if textoFalado and textoFalado != "":
                            if len(textoFalado)<757: #Limite que um id pode ter no firebase (evita que tente gravar uma pergunta muito grande)
                                try:
                                    pergunta = None
                                    try:
                                        print(" \033[33m[FIREBASE]\033[0;0m Verificando Firebase...")
                                        # Busca a pergunta realizada no firebase
                                        pergunta = db.reference("Perguntas").child(textoFalado).get()
                                        # Verifica se a pergunta existe
                                        if pergunta:
                                            if db.reference("Perguntas").child(textoFalado).get()["tipo"] == "resposta":
                                                # Se existir, busca a resposta da pergunta
                                                resposta = db.reference("Perguntas").child(textoFalado).get()["resposta"]
                                            else:
                                                codigo = db.reference("Perguntas").child(textoFalado).get()["codigo"]
                                                try:
                                                    exec(codigo)
                                                except Exception as e:
                                                    print(" \033[31m[ERR]\033[0;0m Erro, "+str(e)+".\033[0;0m")
                                                break
                                    except Exception as e:
                                        print(" \033[31m[ERR]\033[0;0m Erro, "+str(e)+".\033[0;0m")
                                    

                                    # Verifica se a pergunta ou a resposta não existem
                                    if pergunta == None or resposta == [""]:
                                        setarExpressao("respondendo")
                                        falar(["Aguarde, estou pensando", "Aguarde enquanto pesquiso", "Por favor aguarde, estou pesquisando"])
                                        setarExpressao("aguardando")
                                        pensando = True
                                        startAudioThread()
                                        # Se não existir, printa que não encontrou resposta (opcional)
                                        print(" \033[31m[ERR]\033[0;0m Nenhuma resposta encontrada.\033[0;0m")
                                        skin = db.reference(inteligencia.capitalize()).get()["skin"]
                                        modelo = db.reference("GPT").get()
                                        # Printa busca no openai (opcional)
                                        print(" \033[96m[OPENAI]\033[0;0m Conectando-se a https://platform.openai.com...")
                                        print(" \033[96m[OPENAI]\033[0;0m Modelo: "+modelo)
                                        # Salva a pergunta no firebase para que possa seer usada futuramente
                                        try:
                                            db.reference("Perguntas").child(textoFalado).set({"pergunta": textoFalado, "resposta": [""], "codigo": "", "data": int(time.time()), "prioridade": False, "tipo": "resposta"})
                                        except Exception as e:
                                            print(" \033[31m[ERR]\033[0;0m Erro, " + str(e))
                                        
                                        

                                        instrucoes = ""
                                        if skin == "citec":
                                            instrucoes = "Você é um assistente virtual chamado totem, você foi desenvolvido pelo centro de inovação tecnológica do cesmac. Sua resposta deve ter no máximo 300 caracteres"
                                        else:
                                            instrucoes = "Você é um assistente virtual chamado totem, você foi desenvolvido pelo centro de inovação tecnológica do cesmac, sua especialidade é ser um "+skin+". Sua resposta deve ter no máximo 300 caracteres"

                                        client = OpenAI(api_key=os.getenv('OPENAI_TOKEN'))

                                        response = client.chat.completions.create(
                                            messages=[
                                                {"role": "system", "content": instrucoes},
                                                {"role": "user", "content": textoFalado},
                                            ],
                                            model=modelo,
                                        )

                                        pensando = False # Define que o som de pensar irá parar de ser executado

                                        # Muda a expressão
                                        setarExpressao("respondendo")
                                        
                                        # Fala a resposta retornada pela open ai
                                        falar([response.choices[0].message.content])

                                        playsound("audios/sleep.mp3")
                                    else: 
                                        pensando = False # Define que o som de pensar irá parar de ser executado
                                        respostas = resposta
                                        setarExpressao("respondendo")
                                    parar = True

                                except Exception as e:
                                    parar = True
                                    pensando = False # Define que o som de pensar irá parar de ser executado
                                    print(" \033[31m[ERR] Ocorreu um erro ao conectar - "+str(e)+".\033[0;0m")
                                    setarExpressao("triste")
                                    falar(["Desculpe não consegui me conectar com os servidores. Espero conseguir responder você assim que possível."])
                                    
                                    playsound("audios/sleep.mp3")
                        else:
                            setarExpressao("respondendo")
                            numeroRespostas = numeroRespostas + 1
                            # Fala que não entendeu
                            falar(respostas)
                            playsound("audios/sleep.mp3")
                            parar = True
                            
                    else:
                        # soma uma resposta no registro
                        numeroRespostas = numeroRespostas + 1
                    if respostas != ["Desculpa, não entendi o que você falou"]:
                        # Fala a resposta fornecida pelos if's else's
                        if len(respostas) > 0:
                            falar(respostas)
                        parar = True
                        playsound("audios/sleep.mp3")
                        
                    # Reseta a quantidade de respostas
                    escutado = textoFalado
                    respostas = []
                    numeroRespostas = 0
                textoFalado = ""
        
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
    try:
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
    except Exception as e:
        print("[LOG] Erro: "+str(erro))
        falar(["Ocorreu um erro na inicialização do microfone."])

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


print(" \033[32m[LOG]\033[0;0m Verificando conexão com à internet. Por favor, aguarde!...")

if(checa_internet()==True):
    print(" \033[32m[LOG]\033[0;0m Conectado ao serviço de reconhecimento de voz do google.")
else:
    print(" \033[31m[ERR] ERRO CRÍTICO! Falha ao conectar-se.\033[0;0m")

    ReproducaoVideo.offline = True
    falar(["Falha de conexão. Estou offline."])
    
# Inicializar o speech recognition
recognizer = speech_recognition.Recognizer()
# recognizer.set_threshold = 500
recognizer.dynamic_energy_threshold = False
recognizer.energy_threshold = 0   # menor = escuta mais longe | maior = escuta menos - ideal: 50 a 4000
ajustarRuidos()

print(" \033[32m[LOG]\033[0;0m Iniciando Expressões...")


expressoesConecta = ReproducaoVideo('ausente')


main()