#함수를 정의
def add(a, b):
    return a + b

#함수를 호출
result = add(5, 3)
print(result)  # 출력: 8

#배열형식을 연습
lst = ["사과","배","바나나","포도"]
print(len(lst))  # 출력: 4

for fruit in lst:
    print(fruit)

#리스트에 값을 추가,삭제
lst.append("딸기")
print(lst)  # 출력: ['사과', '배', '바나나', '포도', '딸기']
lst.remove("배")
print(lst)  # 출력: ['사과', '바나나', '포도', '딸기']

#Tuple은 한방에 입력하고 출력하는 배열형태
tp = (100,200,300)
print(len(tp))  # 출력: 3
print(type(tp))  # 출력: <class 'tuple'>
for item in tp:
    print(item)

#함수를 정의
def times(a, b):
    return a * b, a +b 

#함수를 호출
result = times(3,4)
print(result)  # 출력: (12, 7)

