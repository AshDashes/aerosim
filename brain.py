import random
import math

class neural_network:
    def __init__(self, num_inputs = 5, num_hidden = 6, num_outputs = 2):
        self.num_inputs = num_inputs
        self.num_hidden = num_hidden
        self.num_outputs = num_outputs

        self.w_ih = [[random.uniform(-1.0, 1.0) for _ in range(num_hidden)] for _ in range(num_inputs)]

        self.b_h = [random.uniform(-1.0, 1.0) for _ in range(num_hidden)]

        self.w_ho = [[random.uniform(-1.0, 1.0) for _ in range(num_outputs)] for _ in range(num_hidden)]

        self.b_o = [random.uniform(-1.0, 1.0) for _ in range(num_outputs)]

    def feedforward(self, inputs):
        hidden = []
        for j in range(self.num_hidden):
            val = self.b_h[j]
            for i in range(self.num_inputs):
                val += inputs[i] * self.w_ih[i][j]

            hidden.append(math.tanh(val))

        outputs = []
        for k in range(self.num_outputs):
            val = self.b_o[k]
            for j in range(self.num_hidden):
                val += hidden[j] * self.w_ho[j][k]

            outputs.append(math.tanh(val))

        return outputs

    def clone(self):
        new_net = neural_network(self.num_inputs, self.num_hidden, self.num_outputs)

        new_net.w_ih = [row[:] for row in self.w_ih]
        new_net.b_h = self.b_h[:]
        new_net.w_ho = [row[:] for row in self.w_ho]
        new_net.b_o = self.b_o[:]
        return new_net

    def mutate(self, rate):
        def change(val):
            if random.random() < rate:
                return val + random.uniform(-0.15, 0.15)
            return val

        self.w_ih = [[change(w) for w in row] for row in self.w_ih]
        self.b_h = [change(b) for b in self.b_h]
        self.w_ho = [[change(w) for w in row] for row in self.w_ho]
        self.b_o = [change(b) for b in self.b_o]

def crossover(net1, net2):
    child = neural_network(net1.num_inputs, net1.num_hidden, net1.num_outputs)

    def cross_mat(m1, m2):
        return [[random.choice([m1[i][j], m2[i][j]]) for j in range(len(m1[0]))] for i in range(len(m1))]

    def cross_vec(v1, v2):
        return [random.choice([v1[i], v2[i]]) for i in range(len(v1))]

    child.w_ih = cross_mat(net1.w_ih, net2.w_ih)
    child.b_h = cross_vec(net1.b_h, net2.b_h)
    child.w_ho = cross_mat(net1.w_ho, net2.w_ho)
    child.b_o = cross_vec(net1.b_o, net2.b_o)
    
    return child