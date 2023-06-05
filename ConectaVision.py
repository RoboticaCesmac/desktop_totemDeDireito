# Parte do projeto tem como base o projeto do Canal do Sandeco
import cv2
import time
import glob
import numpy as np
from imutils import face_utils
import dlib
from mediapipe.framework.formats import landmark_pb2
from pythonosc import udp_client
from pythonosc.osc_message_builder import OscMessageBuilder
import mediapipe as mp
import face_recognition
import os
import uuid


frameRosto = None # É a imagem do rosto
nomeRosto = "" # é o nome do rosto que será cadastrado
nomeRostoReconhecido = "Desconhecido" # é o nome do rosto que foi detectado/reconhecido
faceDetectada = False # guarda o estado da detecção facial
detector = dlib.get_frontal_face_detector() # modelo de detecção facial
FacesConhecidasEncodings = [] # são as embeddings das faces que podem ser reconhecidas
NomesDasFacesConhacidas = [] # é o nome das faces
img = face_recognition.load_image_file("examples/template/template.png") # é a face que é carregada inicialmente
imgEncoding = face_recognition.face_encodings(img)[0]
# Carregar Faces Cadastradas
os.chdir("Examples") # é o diretório das faces cadastradas, o nome do arquivo é composto por nome@id

# carrega todas as pessoas reconhecidas
for file in glob.glob("*.png"):
    directory = file
    imgImport = face_recognition.load_image_file(directory)
    imgImportEncoding = face_recognition.face_encodings(imgImport)[0]
    file = file[:-4]
    NomesDasFacesConhacidas.append(file.split("@")[0])
    FacesConhecidasEncodings.append(imgImportEncoding)

os.chdir(os.path.dirname(os.getcwd()))
tempos = []

OSC_ADDRESS = "/mediapipe/pose"

# gera uma média de FPS
def AVG(array):
    return sum(array)/len(array)

#salva pose no osc client
def send_pose(client: udp_client,
              landmark_list: landmark_pb2.NormalizedLandmarkList):
    if landmark_list is None:
        client.send_message(OSC_ADDRESS, 0)
        return

    # create message and send
    builder = OscMessageBuilder(address=OSC_ADDRESS)
    builder.add_arg(1)
    for landmark in landmark_list.landmark:
        builder.add_arg(landmark.x)
        builder.add_arg(landmark.y)
        builder.add_arg(landmark.z)
        builder.add_arg(landmark.visibility)
    msg = builder.build()
    client.send(msg)



# cria client osc e inicializa mediapipe
client = udp_client.SimpleUDPClient("127.0.0.1", 7500, True)
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
        smooth_landmarks=False,
        static_image_mode=True,
        model_complexity=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5)
connections = mp_pose.POSE_CONNECTIONS

# detector de marcas faciais
facePredictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")

# salva o maior tempo que demorou para processar um frame
valorMaximoTempoProcessamento=0

# se quiser poupar desempenho, desative o modo visual, isso irá fazer com que as interações não sejam renderizadas, apenas processadas
modo_visual = "ativado"

# delimite aqui quais modos de manipulação de imagem você vai usar, separe-os por vírgulas. Deixe a string vazia se não for usar nenhum modo
# modos disponíveis: rastreamento de poses, rastreamento de objetos, rastreamento facial, reconhecimento facial
modo = "rastreamento de poses, rastreamento de objetos, rastreamento facial, reconhecimento facial"

# detector de faces
detectorFacial = dlib.get_frontal_face_detector()

# carrega as classes do yolo
lbls = list()
with open(glob.glob("yolo/*.txt")[0], "r") as f:
    lbls = [c.strip() for c in f.readlines()]

# carrega o yolo
net = cv2.dnn.readNetFromDarknet(glob.glob("yolo/*.cfg")[0], glob.glob("yolo/*.weights")[0])

camada = net.getLayerNames()
camada = [camada[i - 1] for i in net.getUnconnectedOutLayers()]

# é chamado de outro arquivo e cadastra uma face - retorna true se conseguir cadastrar
def cadastrarRosto():
    try:
        # gera um hash aleatório
        hex = uuid.uuid4().hex
        # cria um arquivo com o nome aleatório como "arquivo@12ab"
        arquivo = nomeRosto+"@"+hex[0]+hex[1]+hex[2]+hex[3]
        # adiciona a extensão png
        file = arquivo +".png"
        # pega o embedding da face que está sendo processada agora
        encoding = face_recognition.face_encodings(frameRosto[:, :, ::-1])[0]
        # salva o nome da pessoa
        NomesDasFacesConhacidas.append(nomeRosto)
        # salva o embedding
        FacesConhecidasEncodings.append(encoding)
        # salva a imagem
        cv2.imwrite("Examples/"+file,frameRosto)
        # retorna true para sucesso
        return True
    except Exception as e:
        # retorna um erro False
        return False

# Reconhece rostos
def reconhecerRostos(img):
    # pega o nome do rosto que está sendo reconhecido no momento
    global nomeRostoReconhecido
    # pega a variável que define se apenas uma face na tela
    global faceDetectada
    # inverte a imagem que vem da câmera
    frame = cv2.flip(img, 180)
    #BGR_PARA_RGB
    rgb_frame = frame[:, :, ::-1]
    # pega a localização de faces na imagem
    face_locations = face_recognition.face_locations(rgb_frame)
    # verifica se há apenas um rosto na  imagem
    if len(face_locations)==1:
        faceDetectada = True
    else:
        faceDetectada = False

    # pega os embeddings das faces detectadas
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

    # corre as faces detecetadas em um for
    for (x, y, w, h), face_encoding in zip(face_locations, face_encodings):

        # compara as faces detectadas com as faces conhecidas
        matches = face_recognition.compare_faces(FacesConhecidasEncodings, face_encoding)
        # define o nome como desconhecido para que ele seja usado caso não detecte nada
        name = "Desconhecido"

        # pega qual face possui uma distância menor | é um valor de 0 até 1 | não é a porcentagem de chance 
        face_distances = face_recognition.face_distance(FacesConhecidasEncodings, face_encoding)

        # a probabilidade é definda pegando o valor 1 e subtraindo a menor distância e multiplicando por 100 | (1 - D) * 100 
        prob = (1 - np.min(face_distances)) * 100 or "100%"
        # pega qual o index da face que foi detectada para comparar com o vetor de nomes das faces conhecidas
        best_match_index = np.argmin(face_distances)
        
        # para filtrar a imprecisão, precisa ter uma probabilidade maior que 60 (o ideal seria 99)
        if matches[best_match_index] and prob > 60:
            # pega o nome da pessoa detectada
            nomeRostoReconhecido = NomesDasFacesConhacidas[best_match_index]
            # monta uma string com o nome e probabilidade "nome | 100%"
            name = NomesDasFacesConhacidas[best_match_index] + " | " + str(int(prob)) + "%"
        else:
            name = name + " | " + str(int(prob)) + "%"
        # define uma ponte para escrever
        fonte = cv2.FONT_HERSHEY_DUPLEX
        # cria o texto abaixo do rosto
        cv2.putText(frame, name, (25, 60), fonte, 1.5, (0,255,0), 1)
    return frame



#detecta objetos em uma imagem
def detectarObjetos(image, nn):
    #guarda  a altura e largura dos objetos
    (altura, largura) = image.shape[:2]

    # salva os dados da imagem
    blob = cv2.dnn.blobFromImage(image, 1 / 255, (416, 416), swapRB=True, crop=False)
    #seta a imagem de entrada
    nn.setInput(blob)
    #realiza detecção de objetos
    resultados = nn.forward(camada)

    #salva o local das caixas de detecção, nível de confiança e id da classe detecetada
    boxes = list()
    confidences = list()
    class_ids = list()

    #para cada detecção...
    for output in resultados:
        for deteccao in output:
    
            #pega qual foi o objeto com maior probabilidade de ter sido detectado (nível de confiança)
            confianca = deteccao[5:][np.argmax(deteccao[5:])]

            #verifica se o nível de confiança é seguro pora evitar falso-positivos
            if confianca > 0.5:
                #salva as posições do retangulo que sera desenhado na imagem
                box = deteccao[0:4] * np.array([largura, altura, largura, altura])
                (center_x, center_y, w, h) = box.astype("int")

                x = int(center_x - (w / 2))
                y = int(center_y - (h / 2))

                boxes.append([x, y, int(w), int(h)])
                confidences.append(float(confianca))
                class_ids.append(np.argmax(deteccao[5:]))

    resultados = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)
    if len(resultados) > 0:
        for i in resultados.flatten():
            (x, y) = (boxes[i][0], boxes[i][1])
            (w, h) = (boxes[i][2], boxes[i][3])

       
     
            cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 1)
            # cv2.circle(image, center, radius, (0, 255, 0), 1)

            text = "{}: {:.2f}%".format(lbls[class_ids[i]], confidences[i]*100)
            
            
            cv2.putText(
                image, text, (x, y - 5), cv2.FONT_HERSHEY_PLAIN, 1, (0, 255, 0), 1
            )
    return image


# detecta rostos em uma imagem passada por parâmetro
def detectarRostos(img):
    #detecta rostos
    rects = detectorFacial(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 1)

    #para cada rosto detectado
    for (i, rect) in enumerate(rects):
	    #guarda as marcas faciais
        shape = face_utils.shape_to_np(facePredictor(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), rect))

	    # salva as cordenadas da caixa de marcação
        (x, y, w, h) = face_utils.rect_to_bb(rect)
        #guarda o centro do rosto para plotar um circulo
        center = (int((x+w/2)), int(y+h/2))
        #guarda o raio do circulo
        radius = int(((x+w) - x))

        #cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.circle(img, center, radius-30, (0, 255, 0), 1)

	    # desenha um circulo nos rostos detectados
        for (x, y) in shape:
            cv2.circle(img, (x, y), 2, (0, 255, 0), -1)
	
    return img

def detectaPoses(img):
    image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # To improve performance, optionally mark the image as not writeable to
    # pass by reference.
    image.flags.writeable = False
    results = pose.process(image)

    # send the pose over osc
    send_pose(client, results.pose_landmarks)

    # Draw the pose annotation on the image.
    image.flags.writeable = True
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    mp_drawing.draw_landmarks(image, results.pose_landmarks, connections)

    return image



"""
Define um filtro colorido para a imagem, essa função é puramente perfumaria, usada para dar um toque mais robótico, não é ativada por padrão
"""
def filtroImagem(frame):
    b, g, r = cv2.split(frame)
    zeros_ch = np.zeros(frame.shape[0:2], dtype="uint8")
    frame = cv2.merge([b, zeros_ch, zeros_ch])
    return frame



def capturarMovimentos():
    global frameRosto
    
    # Carregar Webcam
    cam = cv2.VideoCapture(0)

    # Para cada frame...
    while True:
        try:
            # Armazena imagem em variavel
            ret, img = cam.read()
            frameRosto = img
            # (h, w) = img.shape[:2]

            #salva quando começa a contar o tempo gasto para processar
            start_time = time.time()

            if "reconhecimento facial" in modo:
                img = reconhecerRostos(img)
            if "rastreamento de poses" in modo:
                img = detectaPoses(img)
            if "rastreamento de objetos" in modo:
                img = detectarObjetos(img, net)
            if "rastreamento facial" in modo:
                img = detectarRostos(img)
            #salva quando para de contar o tempo gasto para processar
            end_time = time.time()

            #pega o maior valor apresentado no tempo gasto para processar
            global valorMaximoTempoProcessamento
            if (end_time-start_time)>valorMaximoTempoProcessamento:
                valorMaximoTempoProcessamento = end_time-start_time
            tempos.append(end_time-start_time)
            if(len(tempos)>20):
                tempos.pop(0)

            
            #verifica se deve mostrar informações na imagem
            if (modo_visual == "ativado"):
                
                # #printa o tempo máximo registrado para processar
                # cv2.putText(
                #     img, "MAX: " + str(int(valorMaximoTempoProcessamento*1000)) + "MS", (25, 25), cv2.FONT_HERSHEY_PLAIN, 1, (0, 0, 255), 1
                # )
                # cv2.putText(
                #     img, "AVG: "+ str(int(AVG(tempos)*1000)) + "MS", (25, 50), cv2.FONT_HERSHEY_PLAIN, 1, (0, 0, 255), 1
                # )
                # #registra em tempo real o tempo gasto para processar
                # cv2.putText(
                #     img, "NOW: " + str((int((end_time-start_time)*1000))) + "MS", (25, 75), cv2.FONT_HERSHEY_PLAIN, 1, (0, 0, 255), 1
                # )
                
                # height = img.shape[0]
                # width = img.shape[1]

                # cv2.putText(img, "INTERFACE DO SISTEMA: "+modo_visual.upper(),
                #             (int(width*0.01), int(height*0.05)), cv2.FONT_HERSHEY_PLAIN,  1, (255, 255, 255), 1)
                # cv2.putText(img, "MODO: " + modo.upper(),
                #             (int(width*0.6), int(height*0.95)), cv2.FONT_HERSHEY_PLAIN,  1, (255, 255, 255), 1)
                
                #declara o tamanho da janela para tela cheia
                # cv2.namedWindow("Conecta Vision", cv2.WND_PROP_FULLSCREEN)
                # cv2.moveWindow("Conecta Vision", -480, 601)


                img = cv2.resize(img, (600, 400))
                #muda para tela cheia
                # cv2.setWindowProperty(
                #     "Conecta Vision", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

                return img
                # # Plotar imagem
                # cv2.imshow("Conecta Vision", img)

                # # Aguarda pressionar "q" para encerrar o programa
                # key = cv2.waitKey(1)
                # if key == ord('q') or key == ord('Q'):
                #     break
        except Exception as e:
            print(e)

    # Libera acesso à webcam
    cam.release()

    # Destroi as janelas criada
    cv2.destroyAllWindows()



