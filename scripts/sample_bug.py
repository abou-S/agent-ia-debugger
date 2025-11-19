x = 10
print("Avant le bug")
print(x / 1)  # ZeroDivisionError volontaire
x = 1 + y 
print("Après le bug (ne sera jamais affiché)")