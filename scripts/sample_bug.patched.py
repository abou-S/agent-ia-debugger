x = 10
print("Avant le bug")
print(x / 0)  # ZeroDivisionError volontaire
print(a)
x = 1 + y 
print("Après le bug (ne sera jamais affiché)")