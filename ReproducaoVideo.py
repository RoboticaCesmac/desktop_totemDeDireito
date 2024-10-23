# importing required libraries
import cv2  # OpenCV library 
from cv2 import CAP_PROP_POS_FRAMES
from threading import Thread # library for multi-threading
import sys
import platform
import ConectaVision
import numpy as np
from firebase_admin import db
import time

corDosOlhos = "#ffffff"
apresentacaoLocal = False

frameVisao = None

ConectaVision.iniciarCapturaDeImagem()

#pega a imagem da visao
def visao():
    global frameVisao
    while True:
        frameVisao = ConectaVision.capturarMovimentos()


thread = Thread(target=visao, args=())
thread.daemon = True  # https://stackoverflow.com/questions/11815947/cannot-kill-python-script-with-ctrl-c
thread.start()

def hex2rgb(hex_string):
    # Remove o caractere '#' da string se estiver presente
    hex_string = hex_string.lstrip('#')
    # Converte a string hexadecimal em valores inteiros
    red = int(hex_string[0:2], 16)
    green = int(hex_string[2:4], 16)
    blue = int(hex_string[4:6], 16)
    # Retorna os valores RGB como três variáveis separadas
    return red, green, blue



def colorirFrame(frame):
    global corDosOlhos
    if(corDosOlhos != "#ffffff"):
        r, g, b = hex2rgb(corDosOlhos)

        rgb_norm = np.array([b, g, r]) / 255

        frame[:, :, :3] = np.multiply(frame[:, :, :3], rgb_norm)

    return frame



"""
# Tutorial OpenCV - Reprodução de vídeo: https://docs.opencv.org/4.x/dd/d43/tutorial_py_video_display.html
# Tutorial OpenCV - Reprodução de vídeo com multithread: https://gvasu.medium.com/faster-real-time-video-processing-using-multi-threading-in-python-8902589e1055
"""
class ReproducaoVideo:
    mostraSkin = True
    mostraTela = True
    telaDestruida = False
    offline = False

    # Método de inicialização
    def __init__(self, expressao="ausente"):
        self.video = "expressoes/expressoes_conecta.mp4"
    
        # Carregar video
        self.capturaVideo = cv2.VideoCapture(self.video)
        if(self.capturaVideo.isOpened() == False):
            print(" \033[32m[LOG]\033[0;0m  \033[31m[Exiting] Erro ao abrir video stream ou arquivo\033[0;0m:")
            exit(0)
        
        print(" \033[32m[LOG]\033[0;0m Expressão carregada")

        # Thread
        self.thread = Thread(target=self.reproduzirFrames, args=())
        self.thread.daemon = True  # https://stackoverflow.com/questions/11815947/cannot-kill-python-script-with-ctrl-c
        self.thread.start()

        # Intervalos de frames das expressoes
        self.aguardando = [120, 221]
        self.ausente = [1, 118]
        self.respondendo = [223, 307]
        self.triste = [308, 348]

        self.estado = expressao
        self.skinAtiva =  "citec"
        try:
            self.skinAtiva = db.reference("Totem").get()["skin"]
        except Exception as e:
            pass
        self.introExecutada = False
        self.fadeInExecutado = True
        self.skinInativa = None

    def reproduzirFrames(self):
        global corDosOlhos

        # Skins do totem
        # expressão facial que será exibida na inicialização
        self.skinIntroExpressao = cv2.VideoCapture('expressoes/expressao-ausente.mp4')

        # skin do advogado
        self.skinAdvogado = cv2.VideoCapture('expressoes/skins/advogado/skin.mp4')
        self.skinIntroAdvogado = cv2.VideoCapture('expressoes/skins/advogado/intro.mp4')
        self.skinOutAdvogado = cv2.VideoCapture('expressoes/skins/advogado/out.mp4')

        # skin do psicólogo
        self.skinPsicologo = cv2.VideoCapture('expressoes/skins/psicologo/skin.mp4')
        self.skinIntroPsicologo = cv2.VideoCapture('expressoes/skins/psicologo/intro.mp4')
        self.skinOutPsicologo = cv2.VideoCapture('expressoes/skins/psicologo/out.mp4')
        
        # skin do citec
        self.skinIntroCitec = cv2.VideoCapture('expressoes/skins/citec/intro.mp4')
        self.skinCitec = cv2.VideoCapture('expressoes/skins/citec/skin.mp4')
        self.skinOutCitec = cv2.VideoCapture('expressoes/skins/citec/out.mp4')

        # skin de personal
        self.skinIntroPersonal = cv2.VideoCapture('expressoes/skins/personal/intro.mp4')
        self.skinPersonal = cv2.VideoCapture('expressoes/skins/personal/skin.mp4')
        self.skinOutPersonal = cv2.VideoCapture('expressoes/skins/personal/out.mp4')

        # splash do citec
        self.splash = cv2.VideoCapture('expressoes/splash.mp4')

        # Controlador do clique do mouse na Skin
        def mouseController(event, x,y,flags,params):
            # Obtém o tamanho da janela
            window_rect = cv2.getWindowImageRect("Skin")
            window_width = window_rect[2]  # Largura da janela
            
            # Define a largura e altura da área clicável
            area_width = 140
            area_height = 140
            
            # Define as coordenadas do retângulo no canto superior direito
            top_left_x = window_width - area_width      
            top_left_y = 0                           
            bottom_right_x = window_width   
            bottom_right_y = area_height                
            
            # Verifica se o evento é um clique com o botão esquerdo
            if event == cv2.EVENT_LBUTTONDOWN:
                if top_left_x <= x <= bottom_right_x and top_left_y <= y <= bottom_right_y:
                    global apresentacaoLocal
                    apresentacaoLocal = True

        self.frame_counter = 1
        self.transicao = False

        while True:
            retIntro, frameIntro = self.splash.read()
            if(retIntro):
                cv2.namedWindow("Skin", cv2.WND_PROP_FULLSCREEN)
                #cv2.moveWindow("Skin", -480, 601)
                cv2.setWindowProperty("Skin",cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)
                cv2.namedWindow("janela", cv2.WND_PROP_FULLSCREEN)
                cv2.setWindowProperty("janela",cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)
                cv2.imshow("janela", frameIntro)
                cv2.imshow("Skin", frameIntro)
                cv2.waitKey(1)
            else:
                break

        ultimoFrameSkin = None
        while True:
            # Se não estiver sendo feita a transição para outra expressão
            if(self.transicao == False):
                # executa um fade out antes de sair da animação para uma nova
                if self.skinInativa == "citec" and self.introExecutada == False and self.fadeInExecutado == False:
                    while True:
                        retSkinExpressao, frame = self.skinIntroExpressao.read()
                        retSkinOutCitec, frameSkinOutCitec = self.skinOutCitec.read()
                        if retSkinOutCitec:
                            cv2.imshow("Skin", frameSkinOutCitec)
                            if retSkinExpressao:
                                cv2.imshow("janela", frame if corDosOlhos == "#ffffff" else colorirFrame(frame))
                            cv2.waitKey(1)
                        else:
                            # seta os frames para o início novamente
                            self.skinIntroExpressao.set(CAP_PROP_POS_FRAMES, 0)
                            self.skinOutCitec.set(CAP_PROP_POS_FRAMES, 0)
                            self.fadeInExecutado = True
                            break
                        if not retSkinExpressao:
                            # serve para deixar a expressão em loop
                            self.skinIntroExpressao.set(CAP_PROP_POS_FRAMES, 0)

                # executa um fade out antes de sair da animação para uma nova
                if self.skinInativa == "personal trainer" and self.introExecutada == False and self.fadeInExecutado == False:
                    while True:
                        retSkinExpressao, frame = self.skinIntroExpressao.read()
                        retSkinOutPersonal, frameSkinOutPersonal = self.skinOutPersonal.read()
                        if retSkinOutPersonal:
                            cv2.imshow("Skin", frameSkinOutPersonal)
                            if retSkinExpressao:
                                cv2.imshow("janela", frame if corDosOlhos == "#ffffff" else colorirFrame(frame))
                            cv2.waitKey(1)
                        else:
                            # seta os frames para o início novamente
                            self.skinIntroExpressao.set(CAP_PROP_POS_FRAMES, 0)
                            self.skinOutPersonal.set(CAP_PROP_POS_FRAMES, 0)
                            self.fadeInExecutado = True
                            break
                        if not retSkinExpressao:
                            # serve para deixar a expressão em loop
                            self.skinIntroExpressao.set(CAP_PROP_POS_FRAMES, 0)

                # executa um fade out antes de sair da animação para uma nova
                if self.skinInativa == "advogado" and self.introExecutada == False and self.fadeInExecutado == False:
                    while True:
                        retSkinExpressao, frame = self.skinIntroExpressao.read()
                        retSkinOutAdvogado, frameSkinOutAdvogado = self.skinOutAdvogado.read()
                        if retSkinOutAdvogado:
                            cv2.imshow("Skin", frameSkinOutAdvogado)
                            if retSkinExpressao:
                                cv2.imshow("janela", frame if corDosOlhos == "#ffffff" else colorirFrame(frame))
                            cv2.waitKey(1)
                        else:
                            # seta os frames para o início novamente
                            self.skinIntroExpressao.set(CAP_PROP_POS_FRAMES, 0)
                            self.skinOutAdvogado.set(CAP_PROP_POS_FRAMES, 0)
                            self.fadeInExecutado = True
                            break
                        if not retSkinExpressao:
                            # serve para deixar a expressão em loop
                            self.skinIntroExpressao.set(CAP_PROP_POS_FRAMES, 0)

                # executa um fade out antes de sair da animação para uma nova
                if self.skinInativa == "psicologo" and self.introExecutada == False and self.fadeInExecutado == False:
                    while True:
                        retSkinExpressao, frame = self.skinIntroExpressao.read()
                        retSkinOutPsicologo, frameSkinOutPsicologo = self.skinOutPsicologo.read()
                        if retSkinOutPsicologo:
                            cv2.imshow("Skin", frameSkinOutPsicologo)
                            if retSkinExpressao:
                                cv2.imshow("janela", frame if corDosOlhos == "#ffffff" else colorirFrame(frame))
                            cv2.waitKey(1)
                        else:
                            # seta os frames para o início novamente
                            self.skinIntroExpressao.set(CAP_PROP_POS_FRAMES, 0)
                            self.skinOutPsicologo.set(CAP_PROP_POS_FRAMES, 0)
                            self.fadeInExecutado = True
                            break
                        if not retSkinExpressao:
                            # serve para deixar a expressão em loop
                            self.skinIntroExpressao.set(CAP_PROP_POS_FRAMES, 0)

                # executa um fade in junto com uma animação que pode ser feita em vídeo
                if self.skinAtiva == "citec" and self.introExecutada == False and self.fadeInExecutado == True:
                    while True:
                        retSkinExpressao, frame = self.skinIntroExpressao.read()
                        retSkinIntroCitec, frameSkinIntroCitec = self.skinIntroCitec.read()
                        if retSkinIntroCitec:
                            cv2.imshow("Skin", frameSkinIntroCitec)
                            if retSkinExpressao:
                                cv2.imshow("janela", frame if corDosOlhos == "#ffffff" else colorirFrame(frame))
                            cv2.waitKey(1)
                        else:
                            # seta os frames para o início novamente
                            self.skinIntroExpressao.set(CAP_PROP_POS_FRAMES, 0)
                            self.skinIntroCitec.set(CAP_PROP_POS_FRAMES, 0)
                            self.introExecutada = True
                            self.fadeInExecutado = False
                            break
                        if not retSkinExpressao:
                            self.skinIntroExpressao.set(CAP_PROP_POS_FRAMES, 0)
                # executa um fade in junto com uma animação que pode ser feita em vídeo
                if self.skinAtiva == "personal trainer" and self.introExecutada == False and self.fadeInExecutado == True:
                    while True:
                        retSkinExpressao, frame = self.skinIntroExpressao.read()
                        retSkinIntroPersonal, frameSkinIntroPersonal = self.skinIntroPersonal.read()
                        if retSkinIntroPersonal:
                            cv2.imshow("Skin", frameSkinIntroPersonal)
                            if retSkinExpressao:
                                cv2.imshow("janela", frame if corDosOlhos == "#ffffff" else colorirFrame(frame))
                            cv2.waitKey(1)
                        else:
                            # seta os frames para o início novamente
                            self.skinIntroExpressao.set(CAP_PROP_POS_FRAMES, 0)
                            self.skinIntroPersonal.set(CAP_PROP_POS_FRAMES, 0)
                            self.introExecutada = True
                            self.fadeInExecutado = False
                            break
                        if not retSkinExpressao:
                            self.skinIntroExpressao.set(CAP_PROP_POS_FRAMES, 0)
                if self.skinAtiva == "psicologo" and self.introExecutada == False and self.fadeInExecutado == True:
                    while True:
                        retSkinExpressao, frame = self.skinIntroExpressao.read()
                        retSkinIntroPsicologo, frameSkinIntroPsicologo = self.skinIntroPsicologo.read()
                        if retSkinIntroPsicologo:
                            cv2.imshow("Skin", frameSkinIntroPsicologo)
                            if retSkinExpressao:
                                cv2.imshow("janela", frame if corDosOlhos == "#ffffff" else colorirFrame(frame))
                            cv2.waitKey(1)
                        else:
                            # seta os frames para o início novamente
                            self.skinIntroExpressao.set(CAP_PROP_POS_FRAMES, 0)
                            self.skinIntroPsicologo.set(CAP_PROP_POS_FRAMES, 0)
                            self.introExecutada = True
                            self.fadeInExecutado = False
                            break
                        if not retSkinExpressao:
                            self.skinIntroExpressao.set(CAP_PROP_POS_FRAMES, 0)
                if self.skinAtiva == "advogado" and self.introExecutada == False and self.fadeInExecutado == True:
                    while True:
                        retSkinExpressao, frame = self.skinIntroExpressao.read()
                        retSkinIntroAdvogado, frameSkinIntroAdvogado = self.skinIntroAdvogado.read()
                        if retSkinIntroAdvogado:
                            cv2.imshow("Skin", frameSkinIntroAdvogado)
                            if retSkinExpressao:
                                cv2.imshow("janela", frame if corDosOlhos == "#ffffff" else colorirFrame(frame))
                            cv2.waitKey(1)
                        else:
                            # seta os frames para o início novamente
                            self.skinIntroExpressao.set(CAP_PROP_POS_FRAMES, 0)
                            self.skinIntroAdvogado.set(CAP_PROP_POS_FRAMES, 0)
                            self.introExecutada = True
                            self.fadeInExecutado = False
                            break
                        if not retSkinExpressao:
                            self.skinIntroExpressao.set(CAP_PROP_POS_FRAMES, 0)

                retornoFrameOK, frame = self.capturaVideo.read()

                # manipula a janela do opencv
                if(platform.system() == "Windows"):
                    if self.skinAtiva == "citec":
                        ret, frameSkin = self.skinCitec.read()
                    if self.skinAtiva == "advogado":
                        ret, frameSkin = self.skinAdvogado.read()
                    if self.skinAtiva == "psicologo":
                        ret, frameSkin = self.skinPsicologo.read()
                    if self.skinAtiva == "personal trainer":
                        ret, frameSkin = self.skinPersonal.read()
                    if(ret):
                        if(self.mostraSkin):
                            global frameVisao
                            try:
                                # Colar a imagem1 na parte superior esquerda da imagem2
                                frameSkin[50:50+270, 50:50+345, :] = cv2.resize(frameVisao, (345, 270))
                                cv2.rectangle(frameSkin, (50, 50), (395, 325), (255,255,255), 10)
                                cv2.imshow("Skin", frameSkin)
                            except Exception as e:
                                cv2.imshow("Skin", frameSkin)
                            cv2.setMouseCallback("Skin", mouseController)

                    else:
                        if self.skinAtiva == "advogado":
                            self.skinAdvogado.set(CAP_PROP_POS_FRAMES, 0)
                        if self.skinAtiva == "citec":
                            self.skinCitec.set(CAP_PROP_POS_FRAMES, 0)
                        if self.skinAtiva == "psicologo":
                            self.skinPsicologo.set(CAP_PROP_POS_FRAMES, 0)
                        if self.skinAtiva == "personal trainer":
                            self.skinPersonal.set(CAP_PROP_POS_FRAMES, 0)
                        
   
                self.frame_counter += 1
                # print("Frame "+str(self.frame_counter)+ " do estado "+str(self.estado))
                
                # Reinicia o frame_counter para o frame inicial do estado
                if self.estado == 'ausente':
                    if self.frame_counter == self.ausente[1]:
                        self.frame_counter = self.ausente[0]
                        self.capturaVideo.set(cv2.CAP_PROP_POS_FRAMES, self.ausente[0])
                elif self.estado == 'aguardando':
                    if self.frame_counter == self.aguardando[1]:
                        self.frame_counter = self.aguardando[0]
                        self.capturaVideo.set(cv2.CAP_PROP_POS_FRAMES, self.aguardando[0])
                elif self.estado == 'respondendo':
                    if self.frame_counter == self.respondendo[1]:
                        self.frame_counter = self.respondendo[0]
                        self.capturaVideo.set(cv2.CAP_PROP_POS_FRAMES, self.respondendo[0])
                elif self.estado == 'triste':
                    if self.frame_counter == self.triste[1]:
                        self.frame_counter = self.triste[0]
                        self.capturaVideo.set(cv2.CAP_PROP_POS_FRAMES, self.triste[0])

                # Se tiver conseguido ler o frame corretamente, mostra o resultado em uma janela
                if(retornoFrameOK == True):
                   
                    if self.mostraTela:
  
                        self.telaDestruida = False
                        
                        if self.offline:
                            cv2.rectangle(frame,(3,3),(8,43),(0,0,255),-1)
                            cv2.rectangle(frame,(10,14),(15,43),(0,0,255),-1)
                            cv2.rectangle(frame,(17,24),(22,43),(0,0,255),-1)
                            cv2.rectangle(frame,(24,34),(29,43),(0,0,255),-1)
                            cv2.line(frame,(29,3),(3,43),(0,0,120),2)
                            cv2.line(frame,(3,3),(29,43),(0,0,120),2)
                        cv2.namedWindow("janela", cv2.WND_PROP_FULLSCREEN)
                        cv2.setWindowProperty("janela",cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)
                        cv2.imshow('janela', frame if corDosOlhos == "#ffffff" else colorirFrame(frame))
                    else: 
                  
                        if not self.telaDestruida:
                            self.mostraTela = False
                            self.telaDestruida = True
                            cv2.destroyWindow("janela")
                        
                    # Aguarda um tempo para mostrar o próximo frame (número menores torna a reprodução mais rápida, números maiores, mais lenta). Também coleta se alguma tecla foi pressionada no teclado
                    if(platform.system() == "Windows"):
                        key = cv2.waitKey(1)
                    else:
                        key = cv2.waitKey(1)

                    # Para testes usando o teclado para mudar de expressão
                    # if key == ord('a'):
                    #     self.estado = 'ausente'
                    #     self.capturaVideo.set(cv2.CAP_PROP_POS_FRAMES, self.ausente[0])
                    #     self.frame_counter = self.ausente[0]
                    # if key == ord('b'):
                    #     self.estado = 'aguardando'
                    #     self.capturaVideo.set(cv2.CAP_PROP_POS_FRAMES, self.aguardando[0])
                    #     self.frame_counter = self.aguardando[0]
                    # if key == ord('c'):
                    #     self.estado = 'respondendo'
                    #     self.capturaVideo.set(cv2.CAP_PROP_POS_FRAMES, self.respondendo[0])
                    #     self.frame_counter = self.respondendo[0]
                    # if key == ord('d'):
                    #     self.estado = 'triste'
                    #     self.capturaVideo.set(cv2.CAP_PROP_POS_FRAMES, self.triste[0])
                    #     self.frame_counter = self.triste[0]
                    if key == ord('q'):
                        sys.exit(0)
                        break
                else:
                    print(" \033[32m[LOG]\033[0;0m \033[31m[Err] Sem video\033[0;0m")
                    self.capturaVideo.set(CAP_PROP_POS_FRAMES, 0)
            else:
                # Altera o frame para o valor inicial para a nova expressão escolhida
                self.transicao = False

                if self.estado == 'ausente':
                    self.capturaVideo.set(cv2.CAP_PROP_POS_FRAMES, self.ausente[0])
                    self.frame_counter = self.ausente[0]
                if self.estado == 'aguardando':
                    self.capturaVideo.set(cv2.CAP_PROP_POS_FRAMES, self.aguardando[0])
                    self.frame_counter = self.aguardando[0]
                if self.estado == 'respondendo':
                    self.capturaVideo.set(cv2.CAP_PROP_POS_FRAMES, self.respondendo[0])
                    self.frame_counter = self.respondendo[0]
                if self.estado == 'triste':
                    self.capturaVideo.set(cv2.CAP_PROP_POS_FRAMES, self.triste[0])
                    self.frame_counter = self.triste[0]
        
        # Fecha a janela
        self.capturaVideo.release()
        cv2.destroyAllWindows()

    def alterarEstado(self, estado):
        self.transicao = True
        self.estado = estado

    def alterarSkin(self, skinDestino):
        self.skinInativa = self.skinAtiva
        self.skinAtiva = skinDestino
        try:
            db.reference("Totem").update({"skin": skinDestino})
        except Exception as e:
            pass
        self.introExecutada = False

    
    def alterarCorDoOlho(cor):
        global corDosOlhos
        corDosOlhos = cor

    def getCorDoOlho():
        return corDosOlhos
    
    def getApresentacaoLocal():
        return apresentacaoLocal
    
    def setApresentacaoLocal(valor):
        global apresentacaoLocal
        apresentacaoLocal = valor

