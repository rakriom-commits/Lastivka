import torch
import torch.nn as nn
import torch.optim as optim

class RLTrainer:
    def __init__(self, state_dim=10, action_dim=12, lr=0.001):
        self.model = nn.Sequential(
            nn.Linear(state_dim, 64),
            nn.ReLU(),
            nn.Linear(64, action_dim),
            nn.Softmax(dim=-1)
        )
        self.optimizer = optim.Adam(self.model.parameters(), lr=lr)
        self.memory = []

    def store_experience(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))

    def train(self, epochs=5, gamma=0.99):
        if not self.memory:
            return
        # ⚠️ Простий цикл навчання (скелет, ще без PPO)
        for _ in range(epochs):
            for state, action, reward, next_state, done in self.memory:
                state = torch.tensor(state, dtype=torch.float32)
                pred = self.model(state)
                loss = -torch.log(pred[action]) * reward
                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()
        self.memory.clear()
