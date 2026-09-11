#파이썬연습

#클래스를 정의
class person:
#초기화
    def __init__(self):
    self.name = "default name"
    def printInfo(self):
        print("my name is {0}".format(self.name)) 

p1=person()
p1.printInfo()
