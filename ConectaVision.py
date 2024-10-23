# Parte do projeto tem como base o projeto do Canal do Sandeco
import cv2
import glob
import numpy as np
from imutils import face_utils
import dlib
import mediapipe as mp
import face_recognition
import os
import uuid
import json
from deepface import DeepFace




cam = None #captura da imagem
# ultimaInteracao = 0 # é o tempo desde que interagiu com algém pela câmera
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

# detector de marcas faciais
facePredictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")

# salva o maior tempo que demorou para processar um frame
valorMaximoTempoProcessamento=0

# se quiser poupar desempenho, desative o modo visual, isso irá fazer com que as interações não sejam renderizadas, apenas processadas
modo_visual = "ativado"

# delimite aqui quais modos de manipulação de imagem você vai usar, separe-os por vírgulas. Deixe a string vazia se não for usar nenhum modo
# modos disponíveis: rastreamento de poses, rastreamento de objetos, rastreamento facial, reconhecimento facial, reconhecimento de gestos, reconhecimento de emoções
modo = "reconhecimento de emoções"

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
    # global ultimaInteracao
    # pega o nome do rosto que está sendo reconhecido no momento
    global nomeRostoReconhecido
    # pega a variável que define se apenas uma face na tela
    global faceDetectada
    # inverte a imagem que vem da câmera
    frame = img#cv2.flip(img, 180)
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


def reconhecerEmocoes(image):
    global ultimaInteracao
    mp_drawing = mp.solutions.drawing_utils
    emotion_dict = None
    with open('JSON/emotions.json') as f:
            emotion_dict = json.load(f)
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = detector(gray_image)

    for face in faces:
        x1, y1, x2, y2 = face.left(), face.top(), face.right(), face.bottom()

        shape = face_utils.shape_to_np(facePredictor(gray_image, face))
        for (x, y) in shape:
            cv2.circle(image, (x, y), 2, (0, 255, 0), -1)
    
        face_image = image[y1:y2, x1:x2]

        emotion = DeepFace.analyze(face_image, actions=["emotion"], enforce_detection=False, silent=True)

        try:
            dominant_emotion = emotion[0]["dominant_emotion"]

            if dominant_emotion in emotion_dict.keys():
                cv2.putText(image, emotion_dict[dominant_emotion].upper(), (x1, y1 - 10), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 255, 0), 1)
            else:
                cv2.putText(image, dominant_emotion.upper(), (x1, y1 - 10), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 255, 0), 1)

        except:
            pass
            # print('Emoção não encontrada.')
    return image

#detecta objetos em uma imagem
def detectarObjetos(image, nn):
    global ultimaInteracao
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
	    # salva as cordenadas da caixa de marcação
        (x, y, w, h) = face_utils.rect_to_bb(rect)
        #guarda o centro do rosto para plotar um circulo
        center = (int((x+w/2)), int(y+h/2))
        #guarda o raio do circulo
        radius = int(((x+w) - x))

        #cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.circle(img, center, radius-30, (0, 255, 0), 1)
	
    return img

def detectaPoses(img):
    mp_drawing = mp.solutions.drawing_utils
    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(
            smooth_landmarks=False,
            static_image_mode=True,
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5)
    connections = mp_pose.POSE_CONNECTIONS

    image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # To improve performance, optionally mark the image as not writeable to
    # pass by reference.
    image.flags.writeable = False
    results = pose.process(image)


    # Draw the pose annotation on the image.
    image.flags.writeable = True
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    mp_drawing.draw_landmarks(image, results.pose_landmarks, connections)

    return image

def reconheceGestos(img):
    # global ultimaInteracao
    mp_drawing = mp.solutions.drawing_utils
    mp_hands = mp.solutions.hands
    gestures_dict = None
    special_gestures_dict = None

    with open('JSON/gestures.json') as f:
        gestures_dict = json.load(f)
    with open('JSON/special_gestures.json') as f:
        special_gestures_dict = json.load(f)
    
    with mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7) as hands:
        image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = hands.process(image)

        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        if results.multi_hand_landmarks:
            hand_results = []
            for hand_landmarks in results.multi_hand_landmarks:
                thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
                index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
                ring_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
                pinky_tip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]

                thumb_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_IP]
                index_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_MCP]
                middle_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP]
                ring_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_MCP]
                pinky_mcp = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_MCP]

                thumb_raised = thumb_tip.y < thumb_mcp.y
                index_raised = index_tip.y < index_mcp.y
                middle_raised = middle_tip.y < middle_mcp.y
                ring_raised = ring_tip.y < ring_mcp.y
                pinky_raised = pinky_tip.y < pinky_mcp.y

                conditions = [thumb_raised, index_raised, middle_raised, ring_raised, pinky_raised]
                text = ""

                for gesture, gesture_conditions in gestures_dict.items():
                    if conditions == gesture_conditions:
                        text = gesture
                
                for gesture, special_gesture in special_gestures_dict.items():
                    if conditions == special_gesture["conditions"]:
                        for finger_pair in special_gesture["finger_pairs"]:
                            finger1_tip = hand_landmarks.landmark[finger_pair[0]]
                            finger2_tip = hand_landmarks.landmark[finger_pair[1]]
                            distance = np.sqrt((finger1_tip.x - finger2_tip.x) ** 2 + (finger1_tip.y - finger2_tip.y) ** 2)
                            if distance > special_gesture["max_distance"]:
                                break
                            else:
                                text = gesture
                hand_results.append(text)
                mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            for result in hand_results:
                if result:
                    cv2.putText(image, result, (25, 100), cv2.FONT_HERSHEY_DUPLEX, 1.5, (0,255,0), 1)
        return image

def iniciarCapturaDeImagem():
    global cam
    # Carregar Webcam
    cam = cv2.VideoCapture(0)

def capturarMovimentos():
    global cam
    global frameRosto
    # Para cada frame...

    try:
        # Armazena imagem em variavel
        ret, img = cam.read()
        frameRosto = img
        # (h, w) = img.shape[:2]
        if "reconhecimento de emoções" in modo:
            img = reconhecerEmocoes(img)
        if "reconhecimento facial" in modo:
            img = reconhecerRostos(img)
        if "reconhecimento de gestos" in modo:
            img = reconheceGestos(img)
        if "rastreamento de poses" in modo:
            img = detectaPoses(img)
        if "rastreamento de objetos" in modo:
            img = detectarObjetos(img, net)
        if "rastreamento facial" in modo:
            img = detectarRostos(img)

        #verifica se deve mostrar informações na imagem
        if (modo_visual == "ativado"):
            img = cv2.resize(img, (600, 400))
            return img

    except Exception as e:
        print(e)

    # Libera acesso à webcam
    cam.release()

    # Destroi as janelas criada
    cv2.destroyAllWindows()



