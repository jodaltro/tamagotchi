# Demonstração: Sistema de Comunicação Adaptativa

Este documento demonstra como o pet virtual agora se adapta ao estilo de comunicação do usuário, tornando as conversas mais naturais e menos robóticas.

## Problema Resolvido

**Antes:** O pet tinha respostas robóticas e formais, sem se adaptar ao jeito de falar do usuário.

**Agora:** O pet aprende como você se comunica e adapta suas respostas para combinar com seu estilo!

## Exemplos de Uso

### Exemplo 1: Usuário Informal com Gírias

```python
# Usuário fala de forma descontraída
Usuário: "E aí mano, blz?"
Pet: "Oi! Que massa te conhecer! 😊"

Usuário: "Cara, eu curto mt música 🎵 e jogar tbm 🎮"
Pet: "Show! Me conta mais! 🎵"

Usuário: "vc lembra do que eu gosto??"
Pet: "Massa! Vc gosta de música e jogos! 🎮"
```

**O que o pet aprendeu:**
- Formality: 0.40 (informal)
- Slang usage: 0.51 (usa muitas gírias)
- Emoji usage: 0.18 (usa emojis)
- Estilo: "casual, usa muitas gírias e abreviações"

O pet **adapta** suas respostas para:
- Usar gírias brasileiras: "massa", "show", "vc", "pra", "tá"
- Usar emojis com frequência
- Ser mais descontraído
- Usar abreviações: "mt", "tbm", "pq"

### Exemplo 2: Usuário Formal

```python
# Usuário fala de forma mais formal
Usuário: "Olá, tudo bem com você?"
Pet: "Olá! Fico feliz que veio falar comigo!"

Usuário: "Gostaria de saber mais sobre suas funcionalidades."
Pet: "Claro! Posso conversar, aprender sobre você e me lembrar das nossas conversas."

Usuário: "Obrigado pela informação."
Pet: "Por nada! Fico feliz em ajudar!"
```

**O que o pet aprendeu:**
- Formality: 0.65 (formal)
- Slang usage: 0.05 (quase sem gírias)
- Emoji usage: 0.02 (poucos emojis)
- Estilo: "formal e educado"

O pet **adapta** suas respostas para:
- Manter linguagem mais formal
- Usar menos gírias
- Usar menos emojis
- Ser mais educado e completo

## Como Funciona

### 1. Detecção de Estilo

O sistema analisa cada mensagem do usuário e detecta:

- **Formalidade**: Uso de "você" vs "vc", cumprimentos formais vs informais
- **Gírias**: Palavras como "mano", "cara", "blz", "massa", "kkkk"
- **Emojis**: Quantidade e frequência de uso
- **Expressividade**: Uso de "!", "?", repetição de letras
- **Abreviações**: "mt", "tbm", "pq", "vc", etc.

### 2. Adaptação Gradual

O pet **aprende progressivamente** com cada mensagem:
- Atualiza métricas de estilo usando taxa de aprendizado adaptativa
- Quanto mais você conversa, melhor ele te entende
- Mantém consistência entre conversas (persistido no banco de dados)

### 3. Geração de Respostas Adaptadas

Quando usa **Gemini AI** (com API key configurada):
```
O sistema instrui a IA:
"O usuário se comunica assim: casual, usa muitas gírias e abreviações
COPIE O ESTILO DELE para criar conexão e soar mais natural!
- Seja MUITO informal e descontraído
- Use emojis com frequência (1-2 por mensagem)
- Use MUITAS gírias brasileiras
- Use abreviações: 'vc', 'tb', 'mt', 'pra', 'tá'"
```

Quando usa **respostas de fallback** (sem API key):
```python
# Respostas agora são mais coloquiais por padrão
"Oi! Que massa te conhecer! 😊"
"Show! Me conta mais!"
"Opa, legal! Me fala mais! 😊"
"Dahora! Como assim?"
```

## Configuração

### Para Usar com Gemini AI (Recomendado)

```bash
# Defina a API key do Google Gemini
export GOOGLE_API_KEY="sua-chave-aqui"

# Inicie o servidor
uvicorn tamagotchi.server:app --port 8080
```

### Teste Local

```bash
# Rode os testes
python tamagotchi/test_language_style.py

# Ou teste interativamente
python -c "
from tamagotchi.virtual_pet import VirtualPet

pet = VirtualPet()

# Teste com mensagens informais
pet.user_message('E aí mano, blz?')
print(pet.pet_response())

pet.user_message('Cara, eu curto mt música')
print(pet.pet_response())

# Veja o estilo aprendido
style = pet.state.memory.communication_style
print(f'Estilo: {style.get_style_description()}')
"
```

## Benefícios

✅ **Mais Natural**: O pet fala como você fala  
✅ **Menos Robótico**: Respostas variam e se adaptam  
✅ **Personalizado**: Cada usuário tem uma experiência única  
✅ **Persistente**: O estilo é lembrado entre sessões  
✅ **Automático**: Sem configuração necessária, aprende sozinho  

## Estrutura Técnica

### Novos Arquivos

1. **`language_style_analyzer.py`**
   - Detecta e analisa estilo de comunicação
   - Gera prompts adaptativos para a IA
   - Classe `CommunicationStyle` com métricas

2. **`test_language_style.py`**
   - Testes completos do sistema
   - Validação de detecção e adaptação
   - Testes de persistência

### Arquivos Modificados

1. **`virtual_pet.py`**
   - Atualiza estilo a cada mensagem
   - Usa prompts adaptativos
   - Inclui estilo no contexto da IA

2. **`memory_store.py`**
   - Armazena `CommunicationStyle` na memória
   - Inicializa estilo automaticamente

3. **`language_generation.py`**
   - Respostas de fallback mais coloquiais
   - Múltiplas variações para cada situação
   - Uso de gírias brasileiras

4. **`firestore_store.py`**
   - Serializa/deserializa estilo de comunicação
   - Persiste entre sessões

## API Usage

### Enviar Mensagem

```bash
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "message": "E aí mano, blz?"
  }'
```

### Resposta

```json
{
  "response": "Oi! Que massa te conhecer! 😊"
}
```

O sistema **automaticamente**:
1. Detecta que o usuário usa "E aí", "mano", "blz"
2. Identifica estilo informal
3. Gera resposta adaptada com gírias e emoji
4. Salva o estilo para futuras conversas

## Próximos Passos

Para melhorar ainda mais:

1. **Configurar API Key do Gemini** - Para respostas ainda mais naturais e contextuais
2. **Testar com usuários reais** - Coletar feedback sobre naturalidade
3. **Ajustar pesos** - Refinar detecção de gírias específicas da sua região
4. **Adicionar mais variações** - Expandir respostas de fallback

## Conclusão

O pet virtual agora é **significativamente menos robótico** e mais **natural e adaptativo**. Ele aprende como você fala e adapta suas respostas para combinar com seu estilo, criando uma experiência mais autêntica e personalizada! 🎉
