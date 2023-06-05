import pyttsx3

class _TTS:

    engine = None
    rate = None
    def __init__(self, inteligencia):
        self.engine = pyttsx3.init()
        voices = self.engine.getProperty('voices')
        if inteligencia == "conecta":
            self.engine.setProperty('voice', voices[0].id) 
        else:
            pass
            self.engine.setProperty('voice', voices[3].id) 


    def start(self,text_, ):

        
        self.engine.say(text_)
        self.engine.runAndWait()