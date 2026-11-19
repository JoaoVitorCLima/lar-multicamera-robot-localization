# Localização de robô com múltiplas câmeras

Este repositório é a implementação multicâmera do trabalho de localização
visual do robô. O projeto original [LaR Gazebo](https://github.com/JoaoVitorCLima/lar_gazebo_joao_lima)
é mantido separado e serve apenas como referência experimental.

## Entrega final

O experimento final validado no Gazebo produziu 556 amostras em 37,46 s, com
RMSE planar de 1,34 cm e RMSE tridimensional de 1,41 cm. O relatório completo
está em [`results/final_corrected/analysis.md`](results/final_corrected/analysis.md),
com CSV, métricas, gráfico e vídeo demonstrativo:

- [CSV da avaliação](results/final_corrected/poses.csv)
- [Métricas JSON](results/final_corrected/metrics.json)
- [Gráfico de erros](results/final_corrected/errors.png)
- [Vídeo demonstrativo](results/final_corrected/multi_camera_demo.mp4)

## Arquitetura de localização

O robô possui uma esfera verde fluorescente como marcador visual. As duas câmeras
observam o marcador, os centros são convertidos em raios 3D usando os parâmetros
de `CameraInfo` e as matrizes extrínsecas, e os raios são triangulados no
referencial comum `world`:

```text
/camera_1/image_raw ─┐
                     ├─> triangulate_marker ─> /multi_camera/pose
/camera_2/image_raw ─┘
```

O nó publica a posição tridimensional `x`, `y` e `z`. A orientação do marcador
esférico não é observável; por isso, a orientação publicada é identidade e o
controlador utiliza somente a posição planar. O filtro HSV e o limiar de
circularidade rejeitam regiões verdes alongadas do ambiente e priorizam o blob
esférico.

## Execução integrada no Gazebo

Depois de construir a imagem:

```bash
docker compose build
docker compose run --rm multi_camera_robot_localization \
  roslaunch multi_camera_robot_localization top_view.launch \
  gui:=false record:=true drive:=true
```

O launch inicia o Gazebo com uma cópia do ambiente do laboratório, o Husky com a
esfera verde, duas câmeras de localização, a triangulação 3D, o controlador, a
avaliação e a gravação. Para abrir a interface do
Gazebo, use `gui:=true` e autorize o X11 somente em uma sessão confiável:

```bash
xhost +SI:localuser:$(id -un)
docker compose run --rm multi_camera_robot_localization \
  roslaunch multi_camera_robot_localization top_view.launch gui:=true
xhost -SI:localuser:$(id -un)
```

Para reproduzir somente a validação automatizada:

```bash
docker compose run --rm multi_camera_robot_localization \
  bash -lc 'cd /ws/src/multi_camera_robot_localization && \
  PYTHONPATH=src python3 -m unittest discover -s tests -v'
```

Os arquivos de saída ficam em `results/`. Depois da execução, gere o relatório:

```bash
docker compose run --rm multi_camera_robot_localization \
  rosrun multi_camera_robot_localization report_multi_camera.py \
  /ws/src/multi_camera_robot_localization/results/poses.csv
```

## Próximas etapas

1. validar as matrizes extrínsecas com imagens do cenário real;
2. tratar oclusões, bordas e perda de uma câmera;
3. comparar a triangulação com o ground truth do Gazebo;
4. executar múltiplas trajetórias para a avaliação estatística.

## Execução do núcleo de fusão

### Docker

O ambiente recomendado para Ubuntu 22.04 é o contêiner Ubuntu 20.04/ROS
Noetic. Ele não altera o ROS, os drivers NVIDIA ou os pacotes do sistema host.

Verifique antes:

```bash
docker --version
docker compose version
```

Construa a imagem:

```bash
./scripts/build.sh
```

Execute os testes dentro do contêiner:

```bash
./scripts/test_docker.sh
```

Inicie o núcleo de fusão legado:

```bash
./scripts/run_fusion.sh
```

Esta etapa inicia o ROS Master e o nó de fusão planar legado, mas ainda não
publica imagens. Para a simulação completa, use `top_view.launch`.

### Workspace nativo ROS Noetic

Em um workspace ROS Noetic compilado:

```bash
roslaunch multi_camera_robot_localization fusion.launch
```

Este comando ainda não inicia câmeras nem Gazebo; ele valida a etapa de fusão
planar legada. A execução completa com triangulação usa `top_view.launch`.
