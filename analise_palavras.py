class AnalisePalavras: 
    """ 
        Classe para analisar se uma palavra é ofensiva, retorna 0 em masculino e 1 em feminino
    """ 
    def __init__(self):
        self.__dicionario = {}
        self.__criaDicionario()
    """ Ler linha por linha do arquivo e adiciona no dicionario o valor e o gênero da palavra """
    def __criaDicionario(self):
        #Busca o arquivo
        arquivo = open('.\palavrasProibidas\Palavras.txt', 'r')
        linhas = arquivo.readlines()
        #Salva as palavras no dicionario
        for linha in linhas:
            dado = linha.split(',')
            self.__dicionario[dado[0]] = int(dado[1])
        #Encerra o arquivo
        arquivo.close()
    """ 
        Avalia se o que foi detectado é ofensivo
        @param texto - String a ser avaliada
        @return {score: number}
    """
    def avalia(self, texto): 
        retorno = {'score': 0}
        if (texto in self.__dicionario):
            retorno['score'] += self.__dicionario[texto] 
        return retorno