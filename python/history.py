import readline
def history():
    for i in range(readline.get_current_history_length()):
        print(readline.get_history_item(i + 1))

def save_history(filename):
    hist = []
    for i in range(readline.get_current_history_length()):
        hist.append(readline.get_history_item(i + 1))
    with open(filename, 'w') as stream:
        stream.write("\n".join(hist))
