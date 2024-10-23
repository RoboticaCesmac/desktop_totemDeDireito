import pyttsx3


class _TTS:
    
    engine = None
    rate = None
    def __init__(self):
        try:
            self.engine = pyttsx3.init()
            voices = self.engine.getProperty('voices')
            try:
                self.engine.setProperty('voice', voices[3].id) 
            except Exception as e:
                self.engine.setProperty('voice', voices[0].id) 
        except Exception as e:
            print(e)
            
    def start(self,text_, ):
        try:
            self.engine.say(text_)
            self.engine.runAndWait()
        except Exception as e:
            print(e)
            
        