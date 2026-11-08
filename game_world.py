# 계층적 구조를 갖는 게임 월드
# 0: 배경, 1: 플랫폼, 2: 오브젝트, 3: 캐릭터, 4: 이펙트, 5: UI
world = [[] for _ in range(6)]

# 게임 월드의 객체를 담는 함수
def add_object(o, depth = 0):
    world[depth].append(o)

def remove_object(o):
    for layer in world:
        if o in layer:
            layer.remove(o)
            return

# 게임 로직
def update():
    for layer in world:
        for o in layer:
            o.update()

# 게임 렌더링
def render():
    for layer in world:
        for o in layer:
            o.draw()
