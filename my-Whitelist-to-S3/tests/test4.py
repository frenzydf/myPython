import test3

def return_two_variables():
    num10 = "192.168.1.1"
    variable1 = num10 + "/32"
    variable2 = 20
    variable2+=1
    return (variable1, variable2)

if __name__ == "__main__":
    variable2, variable1 = return_two_variables()
    print(variable1)  # 10
    print(variable2)  # 20
    test3.main()
