# Inteligência da Robô Conecta

Essa aplicação permite que você faça uma pergunta à Conecta após falar a palavra "Conecta". Perguntas como quem é a conecta, sobre o que é o núcleo de robótica, como ela está, que horas são, o que é o submarino rov, além de uma integração com o Chat GPT. A aplicação responde a pergunta e apresenta na tela uma animação representando as expressões de seus olhos, de acordo com seu status (ausente, aguardando pergunta e respondendo). O nome do robô pode variar de acordo com o que for declarado no código ou com o tipo de sistema operacional instalado (Totem ou Conecta).

## Tecnologia

Esse projeto foi desenvolvido com [Python](https://www.python.org/downloads/) e faz uso das dependências listadas abaixo. É recomendado instalá-las com o terminal no modo administrador, para que elas possam ser instaladas globalmente e não dar erro quando o script inicializar com a raspberry. <br/>

# Utilizando o comando simplificado, é possível instalar todas as bibliotecas de uma vez só:

## `pip install -r requirements.txt`

ou instalar individualmente:

### `pip install playsound==1.2.2`
"playsound" para reproduzir arquivos de audio

### `pip install firebase_admin`
"firebase_admin" para poder utilizar o firebase

### `pip install python-dotenv`
"DotEnv" para processar o arquivo .env

### `pip3 install vosk`
"vosk-api" para reconhecimento de voz

### `pip install SpeechRecognition`
"SpeechRecognition" para reconhecer a voz e transformá-la em texto

### `pip3 install pvporcupine`
"Picovoice Porcupine" para reconhecer a palavra de ativação

### `pip install pyaudio`
"PyAudio" para utilizar o microfone no Porcupine - "pyaudio" possibilita a captura de sons através do microfone

### `pip3 install keyboard`
"Keyboard" para iniciar o terminal em tela cheia

### `pip install pyttsx3`
"pyttsx3" para transformar texto em audio

### `pip install gTTS`
"gTTS" para transformar texto em audio (raspbian)

### `pip install requests`
"requests" para consumir APIs

### `pip instal openai`
"requests" para usar o ChatGPT

### `pip install opencv-python`
Visão computacional

### `pip install imutils`
Utilitários para manipulação de imagens

### `pip install mediapipe`
Ferramenta de detecção de poses

### `pip install pythonosc`

### `pip install face_recognition`
Reconhecimento facial

### `pip install uuid`
Geração de hash 

###  `pip install wikipedia`
"wikipedia" para responder perguntas sobre "o que é" e "quem é" (descontinuado após OpenAI)

### `pip install googletrans==3.1.0a0`    
"googletrans" para tradução (desativado, mas pode ser útil no futuro)

## Configuração

Configure todos os dados pedidos no arquivo .env, será necessário uma conta nos serviços como Picovoice, OpenAI, Firebase e OpenWeather. 



# EXECUTAR AUTOMATICAMENTE NO LINUX RASPBIAN

Para fazer o script rodar automaticamente quando a raspberry inicializa, rode o comando `sudo crontab -e` no terminal da raspberry, vá até a última linha e digite `@reboot  sleep 15 && XAUTHORITY=/home/pi/.Xauthority  DISPLAY=:0 sh /home/pi/Desktop/conecta.sh >> /home/pi/Desktop/Conecta/log-inicializacao.txt 2>&1`. Nesse caso o script estava na pasta Conecta que estava no Desktop da Raspberry. <Br/>

Utilizar o script "conecta.sh" como inicializador no crontab

# EXECUTAR AUTOMATICAMENTE NO WINDOWS

Para fazer o script rodar automaticamente quando o windows inicializa, basta criar um arquivo .bat com o seguinte texto digitado nele: 
`@echo off
python c:\somescript.py %*
pause`
e salvá-lo na pasta inicializar do windows. Para abri-la, pode abrir o executar do windows apertando windows + r e colocar `shell:startup`.

## Scripts disponíveis

No diretório do projeto, você pode rodar:

### `python main.py`
ou
### `py main.py`

Para iniciar a aplicação.

## O que falta?

- Melhorar o reconhecimento de voz

## Para ativar a voz masculina no windows - importe o arquivo Microsoft_Daniel.reg

## Links que podem ser úteis
[Fazer a raspberry funcionar com o VGA (quando mostrar "entrada não suportada")](https://forums.raspberrypi.com/viewtopic.php?t=173942)
[Como ativar as vozes ocultas do windows](https://www.thewindowsclub.com/unlock-extra-text-to-speech-voices-in-windows)<br/>
[Como criar um arquivo requirements.txt](https://stackoverflow.com/questions/31684375/automatically-create-requirements-txt)<br/>
[Solucionar erro ao executar o googletrans](https://stackoverflow.com/questions/52455774/googletrans-stopped-working-with-error-nonetype-object-has-no-attribute-group)<br/>
[Playlist: Python Voice Assistant](https://www.youtube.com/watch?v=-AzGZ_CHzJk&list=PLzMcBGfZo4-mBungzp4GO4fswxO8wTEFx) <br/>
[Explicação em português sobre o speech_recognition](https://letscode.com.br/blog/speech-recognition-com-python) <br/>
[Auto run any script on startup for Raspberry Pi 4](https://youtu.be/wVPAHI9on0o) <br/>
[Adicionar sleep 60 antes de executar o script](https://stackoverflow.com/questions/66182730/crontab-doesnt-run-python-script-on-a-raspberry-pi-4) para dar tempo da Raspberry inicializar antes de tentar executá-lo <br/>
[Tkinter/OpenCV funcionar com o crontab](https://stackoverflow.com/questions/50801120/running-a-tkinter-gui-using-crontab) <br/>
[Criar um log na inicialização da raspberry](https://forums.raspberrypi.com/viewtopic.php?t=276808) para saber se o script foi executado. Isso também é útil para saber se houve erros ou não.

