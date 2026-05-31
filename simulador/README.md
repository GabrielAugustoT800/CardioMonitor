# Simulador ESP32 PPG

Simulador de batimentos cardíacos via PPG (PhotoPlethysmoGraphy) pra rodar
o sistema sem hardware ESP32 + MAX30100 real.

## Conteúdo

- `simulador_esp32.cpp` — código fonte C++ que simula leitura de sensor
  e envia POST para a API ML.
- `simulador_esp32.exe` — **binário pre-compilado para Windows x64**. Pronto
  pra executar sem setup adicional.
- `gerador_ibi.py` — gerador Python de IBI (Inter-Beat Interval) usado
  como entrada do simulador.

## Uso rápido (sem recompilar)

```bash
# Em um terminal: gera IBIs
python simulador/gerador_ibi.py

# Em outro terminal: executa simulador
simulador/simulador_esp32.exe
```

Resultado: simulador envia batimentos para a API Azure (ou local), que
classifica via Random Forest e grava no Blob Storage. Dashboard lê o Blob
e exibe em tempo real em `/monitor`.

## Recompilar (se precisar modificar o .cpp)

Requer **Windows + MSYS2 + OpenSSL + g++**. Setup completo:

### 1. Instalar MSYS2

Baixar de https://www.msys2.org/ e seguir instalação padrão.

### 2. Instalar dependências no terminal MSYS2 UCRT64

```bash
pacman -Syu
pacman -S mingw-w64-ucrt-x86_64-gcc
pacman -S mingw-w64-ucrt-x86_64-openssl
pacman -S mingw-w64-ucrt-x86_64-curl
```

### 3. Compilar

```bash
cd simulador/
g++ -o simulador_esp32.exe simulador_esp32.cpp \
    -lssl -lcrypto -lcurl -lws2_32
```

### 4. Conferir

```bash
./simulador_esp32.exe --version
```

## Variáveis de ambiente

O simulador lê:
- `API_URL` — URL da API ML (Azure ou local).
- `API_KEY` — autenticação opcional.

Ver `.env.example` na raiz do projeto.

## Notas

- O `.exe` foi compilado em ambiente MSYS2 UCRT64 com OpenSSL 3.x.
- Em outras versões de OpenSSL, recompilar pode ser necessário.
- Linux/macOS: adaptar compilação (substituir `-lws2_32` por equivalente).
