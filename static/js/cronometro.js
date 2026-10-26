
const visorTempo = document.getElementById("tempo");

const botaoIniciar = document.getElementById("botao-iniciar");
const botaoPausar = document.getElementById("botao-pausar");
const botaoReiniciar = document.getElementById("botao-reiniciar");

const seletorDuracao = document.getElementById("duracao");

let tempoRestante = Number(seletorDuracao.value) * 60;
let intervalo = null;
let sessaoId = null;

let salvandoSessao = false;
let finalizandoSessao = false;

// Controle do tempo real de foco
let tempoFocadoMs = 0;
let inicioTrechoFoco = null;


// Calcula o tempo efetivamente estudado
function calcularTempoFocadoMs() {
    if (inicioTrechoFoco !== null) {
        return tempoFocadoMs + (Date.now() - inicioTrechoFoco);
    }

    return tempoFocadoMs;
}


// Atualiza o visor com base no relógio real
function atualizarCronometro() {
    if (inicioTrechoFoco === null) {
        return;
    }

    const decorridoMs = calcularTempoFocadoMs();
    const decorridoSegundos = Math.floor(decorridoMs / 1000);

    const duracaoEscolhida = Number(seletorDuracao.value) * 60;

    tempoRestante = Math.max(
        0,
        duracaoEscolhida - decorridoSegundos
    );

    atualizarVisor();
}


// Atualiza o tempo exibido na tela
function atualizarVisor() {
    const minutos = Math.floor(tempoRestante / 60);
    const segundos = tempoRestante % 60;

    visorTempo.textContent =
        `${String(minutos).padStart(2, "0")}:` +
        `${String(segundos).padStart(2, "0")}`;
}


// Escolher duração antes de iniciar
seletorDuracao.addEventListener("change", function () {
    if (
        intervalo !== null ||
        sessaoId !== null ||
        salvandoSessao ||
        finalizandoSessao
    ) {
        return;
    }

    tempoRestante = Number(seletorDuracao.value) * 60;
    tempoFocadoMs = 0;
    inicioTrechoFoco = null;

    atualizarVisor();
});


// Criar uma sessão no banco
async function registrarInicioSessao() {
    const resposta = await fetch("/foco/iniciar", {
        method: "POST"
    });

    if (!resposta.ok) {
        throw new Error("Não foi possível registrar a sessão.");
    }

    const dados = await resposta.json();
    return dados.sessao_id;
}


// Salvar a sessão com o tempo efetivo de foco
async function enviarSessao(url) {
    if (sessaoId === null) {
        return false;
    }

    finalizandoSessao = true;

    try {
        const duracaoSegundos = Math.floor(
            calcularTempoFocadoMs() / 1000
        );

        const resposta = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                sessao_id: sessaoId,
                duracao_segundos: duracaoSegundos
            })
        });

        if (!resposta.ok) {
            throw new Error("Não foi possível salvar a sessão.");
        }

        sessaoId = null;
        return true;

    } catch (erro) {
        console.error(erro);

        alert(
            "Não foi possível salvar a sessão. " +
            "Verifique a conexão e tente novamente."
        );

        return false;

    } finally {
        finalizandoSessao = false;
    }
}


// Concluir a sessão
async function finalizarSessao() {
    return await enviarSessao("/foco/finalizar");
}


// Interromper a sessão
async function interromperSessao() {
    return await enviarSessao("/foco/interromper");
}


// Iniciar ou continuar
async function iniciarCronometro() {
    if (
        intervalo !== null ||
        salvandoSessao ||
        finalizandoSessao ||
        tempoRestante <= 0
    ) {
        return;
    }

    if (sessaoId === null) {
        salvandoSessao = true;
        botaoIniciar.disabled = true;

        try {
            sessaoId = await registrarInicioSessao();

        } catch (erro) {
            console.error(erro);

            alert(
                "Não foi possível iniciar a sessão. " +
                "Verifique se o servidor está funcionando."
            );

            return;

        } finally {
            salvandoSessao = false;
            botaoIniciar.disabled = false;
        }
    }

    inicioTrechoFoco = Date.now();

    botaoIniciar.textContent = "Continuar";
    botaoPausar.disabled = false;
    seletorDuracao.disabled = true;

    intervalo = setInterval(async function () {
        atualizarCronometro();

        if (tempoRestante <= 0) {
            clearInterval(intervalo);
            intervalo = null;

            // Registra o fim do trecho de foco
            tempoFocadoMs = calcularTempoFocadoMs();
            inicioTrechoFoco = null;

            botaoIniciar.disabled = true;
            botaoIniciar.textContent = "Salvando...";
            botaoPausar.disabled = true;
            botaoReiniciar.disabled = true;

            const salvou = await finalizarSessao();

            if (salvou) {
                botaoIniciar.textContent = "Concluído";

                alert(
                    "Sessão de foco concluída! " +
                    "Parabéns pelo seu esforço!"
                );
            } else {
                botaoIniciar.textContent = "Tentar salvar novamente";
                botaoIniciar.disabled = false;
            }

            botaoReiniciar.disabled = false;
        }
    }, 200);
}


// Pausar sem encerrar a sessão
function pausarCronometro() {
    if (intervalo === null || inicioTrechoFoco === null) {
        return;
    }

    tempoFocadoMs = calcularTempoFocadoMs();
    inicioTrechoFoco = null;

    clearInterval(intervalo);
    intervalo = null;

    atualizarCronometro();

    botaoIniciar.textContent = "Continuar";
    botaoPausar.disabled = true;
}


// Reiniciar e registrar a interrupção
async function reiniciarCronometro() {
    if (salvandoSessao || finalizandoSessao) {
        return;
    }

    if (intervalo !== null) {
        clearInterval(intervalo);
        intervalo = null;
    }

    // Captura o tempo até o momento da interrupção
    if (inicioTrechoFoco !== null) {
        tempoFocadoMs = calcularTempoFocadoMs();
        inicioTrechoFoco = null;
    }

    botaoReiniciar.disabled = true;
    botaoIniciar.disabled = true;
    botaoPausar.disabled = true;

    let podeReiniciar = true;

    if (sessaoId !== null) {
        podeReiniciar = await interromperSessao();
    }

    if (!podeReiniciar) {
        botaoIniciar.disabled = false;
        botaoIniciar.textContent = "Continuar";
        botaoReiniciar.disabled = false;
        return;
    }

    tempoRestante = Number(seletorDuracao.value) * 60;
    tempoFocadoMs = 0;
    inicioTrechoFoco = null;

    atualizarVisor();

    botaoIniciar.disabled = false;
    botaoIniciar.textContent = "Iniciar foco";
    botaoPausar.disabled = true;
    botaoReiniciar.disabled = false;
    seletorDuracao.disabled = false;
}


// Conectar os botões
botaoIniciar.addEventListener("click", iniciarCronometro);
botaoPausar.addEventListener("click", pausarCronometro);
botaoReiniciar.addEventListener("click", reiniciarCronometro);


// Estado inicial
botaoPausar.disabled = true;
atualizarVisor();
