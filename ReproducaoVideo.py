# importing required libraries
from glob import glob
from operator import truediv
import cv2  # OpenCV library 
from cv2 import CAP_PROP_POS_FRAMES
import time # time library
from threading import Thread # library for multi-threading
import sys
import platform
import ConectaVision
import numpy as np
from firebase_admin import credentials
from firebase_admin import db
import firebase_admin


frameVisao = None

#pega a imagem da visao
def visao():
    global frameVisao
    cont = 0
    while True:
        # start_time = time.time()
        frameVisao = ConectaVision.capturarMovimentos()
        # end_time = time.time()
        # cv2.putText(
        #     frameVisao, "{:.1f}".format((1000/int((end_time-start_time)*1000))) + "FPS", (25, 25), cv2.FONT_HERSHEY_PLAIN, 1, (0, 0, 255), 1
        # )


thread = Thread(target=visao, args=())
thread.daemon = True  # https://stackoverflow.com/questions/11815947/cannot-kill-python-script-with-ctrl-c
thread.start()



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
        self.skinAtiva = db.reference("Conecta").get()["skin"] or "citec"
        self.introExecutada = False
        self.fadeInExecutado = True
        self.skinInativa = None

    def reproduzirFrames(self):
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

        # splash do citec
        self.splash = cv2.VideoCapture('expressoes/splash.mp4')
        # Controlador do clique do mouse na Skin
        def mouseController(event, x,y,flags,params):
            if event == cv2.EVENT_LBUTTONDOWN:
                self.mostraSkin = False
                cv2.destroyWindow("Skin")

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
                                cv2.imshow("janela", frame)
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
                if self.skinInativa == "advogado" and self.introExecutada == False and self.fadeInExecutado == False:
                    while True:
                        retSkinExpressao, frame = self.skinIntroExpressao.read()
                        retSkinOutAdvogado, frameSkinOutAdvogado = self.skinOutAdvogado.read()
                        if retSkinOutAdvogado:
                            cv2.imshow("Skin", frameSkinOutAdvogado)
                            if retSkinExpressao:
                                cv2.imshow("janela", frame)
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
                                cv2.imshow("janela", frame)
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
                                cv2.imshow("janela", frame)
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
                if self.skinAtiva == "psicologo" and self.introExecutada == False and self.fadeInExecutado == True:
                    while True:
                        retSkinExpressao, frame = self.skinIntroExpressao.read()
                        retSkinIntroPsicologo, frameSkinIntroPsicologo = self.skinIntroPsicologo.read()
                        if retSkinIntroPsicologo:
                            cv2.imshow("Skin", frameSkinIntroPsicologo)
                            if retSkinExpressao:
                                cv2.imshow("janela", frame)
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
                                cv2.imshow("janela", frame)
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
                    if(ret):
                        if(self.mostraSkin):
                            global frameVisao
                            try:
                                # Obter as dimensões das duas imagens
                                altura1, largura1, _ = frameVisao.shape
                                altura2, largura2, _ = frameSkin.shape

                                cv2.rectangle(frameVisao, (0, 0), (largura1, altura1), (255,255,255), 20)

                                # Redimensionar a imagem1 para as mesmas dimensões da imagem2
                        
                                frameVisao = cv2.resize(frameVisao, (int(largura2 * 0.18), int(altura2*0.25)))

                                

                                # Obter as novas dimensões da imagem1
                                altura1, largura1, _ = frameVisao.shape

                                # Criar uma nova imagem de saída com as dimensões da imagem2
                                saida = frameSkin.copy()


                                # Colar a imagem1 na parte superior esquerda da imagem2
                                saida[50:50+altura1, 50:50+largura1, :] = frameVisao


                                cv2.imshow("Skin", saida)
                            except Exception as e:
                                cv2.imshow("Skin", frameSkin)
                            #cv2.setMouseCallback("Skin", mouseController)
                            


                    else:
                        if self.skinAtiva == "advogado":
                            self.skinAdvogado.set(CAP_PROP_POS_FRAMES, 0)
                        if self.skinAtiva == "citec":
                            self.skinCitec.set(CAP_PROP_POS_FRAMES, 0)
                        if self.skinAtiva == "psicologo":
                            self.skinPsicologo.set(CAP_PROP_POS_FRAMES, 0)
                        
                # if(not self.mostraSkin):
                #     if cv2.getWindowProperty('Skin', cv2.WND_PROP_VISIBLE) < 0:
                #         cv2.destroyWindow("Skin")
                    


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
                        cv2.imshow('janela', frame)
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
                    if key == ord('c'):
                        self.alterarSkin("citec")
                    if key == ord('p'):
                        self.alterarSkin("psicologo")
                    if key == ord('a'):
                        self.alterarSkin("advogado")
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
        db.reference("Conecta").update({"skin": skinDestino})
        self.introExecutada = False


