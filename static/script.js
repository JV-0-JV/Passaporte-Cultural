/* =========================================================================
   PASSAPORTE CULTURAL — script.js
   Todo o frontend é uma única página. As "telas" (Painel, Biblioteca,
   Repertório, Backup) são apenas <section> que mostramos/escondemos com
   CSS. Tudo se comunica com o backend Flask através de fetch() para os
   endereços que começam com /api/...
   ========================================================================= */

const TIPOS = ['Filme', 'Série', 'Anime', 'Jogo', 'Livro', 'Mangá', 'HQ', 'Visual Novel', 'Novel', 'Podcast', 'Música', 'Outro'];

const STATUS = ['Quero começar', 'Em andamento', 'Concluído', 'Pausado', 'Abandonado'];

const STATUS_CLASSE = {
  'Quero começar': 'status-comecar',
  'Em andamento': 'status-andamento',
  'Concluído': 'status-concluido',
  'Pausado': 'status-pausado',
  'Abandonado': 'status-abandonado',
};

const IDIOMAS_SUGERIDOS = ['Japonês', 'Inglês', 'Espanhol', 'Coreano', 'Francês', 'Alemão', 'Italiano', 'Mandarim', 'Russo', 'Sueco'];
const CORES_IDIOMA = ['#1B2A4A', '#A63A34', '#3F5B4D', '#B08D3E', '#6B4E71', '#B0562C'];

// Tipos que registram progresso em episódios (campo único "Quantidade").
const TIPOS_EPISODIOS = ['Série', 'Anime'];

// Tipos em que a sessão pode trazer páginas E palavras ao mesmo tempo
// (os dois campos aparecem juntos, sem precisar escolher um ou outro).
const TIPOS_PAGINAS_E_PALAVRAS = ['Livro', 'Mangá', 'HQ', 'Novel'];

// Visual Novel só registra palavras — não tem o campo de páginas.
const TIPOS_SO_PALAVRAS = ['Visual Novel'];

// Tipos que não têm uma API de busca automática configurada (ex: "Outro")
const TIPOS_SEM_BUSCA = ['Outro'];

let graficoIdiomas, graficoTipos, graficoSemana;
let midiaDetalheAtual = null;
let tipoMidiaAtual = null;

// ---------------------------------------------------------------------
// FUNÇÕES AUXILIARES
// ---------------------------------------------------------------------

async function api(caminho, opcoes = {}) {
  const resposta = await fetch(caminho, {
    headers: { 'Content-Type': 'application/json' },
    ...opcoes,
  });
  if (!resposta.ok) {
    const erro = await resposta.json().catch(() => ({ erro: 'Erro desconhecido' }));
    throw new Error(erro.erro || 'Erro na requisição');
  }
  const tipoConteudo = resposta.headers.get('content-type') || '';
  if (tipoConteudo.includes('application/json')) return resposta.json();
  return resposta.text();
}

function dataLocalISO(data) {
  // Formata uma data como YYYY-MM-DD usando o horário LOCAL do navegador.
  // Não usar toISOString() aqui: ele converte para UTC antes de formatar,
  // então sessões registradas à noite (Brasil = UTC-3) acabavam caindo
  // no dia seguinte (ex: 22h de 02/08 vira 01h de 03/08 em UTC).
  const ano = data.getFullYear();
  const mes = String(data.getMonth() + 1).padStart(2, '0');
  const dia = String(data.getDate()).padStart(2, '0');
  return `${ano}-${mes}-${dia}`;
}

function escapeHtml(texto) {
  const div = document.createElement('div');
  div.textContent = texto ?? '';
  return div.innerHTML;
}

function formatarEstrelas(nota) {
  // Aceita notas com meia-estrela (ex: 3.5). Arredonda para o meio mais
  // próximo (0.5) antes de desenhar, caso algum valor "torto" apareça.
  // A meia-estrela é montada com HTML/CSS (span com largura 50% sobreposto
  // a uma estrela vazia) em vez de um caractere unicode de meia-estrela,
  // porque glifos como ⯨ não existem na maioria das fontes.
  const valor = Math.round(nota * 2) / 2;
  const cheias = Math.floor(valor);
  const temMeia = valor - cheias === 0.5;
  const vazias = 5 - cheias - (temMeia ? 1 : 0);
  const spanMeia = '<span class="estrela-meia">★</span>';
  return '★'.repeat(cheias) + (temMeia ? spanMeia : '') + '☆'.repeat(Math.max(0, vazias));
}

function corIdioma(idioma) {
  let soma = 0;
  for (let i = 0; i < idioma.length; i++) soma += idioma.charCodeAt(i);
  return CORES_IDIOMA[soma % CORES_IDIOMA.length];
}

function formatarDataCurta(iso) {
  const partes = iso.split('-');
  if (partes.length !== 3) return iso;
  return `${partes[2]}/${partes[1]}`;
}

function baixarArquivoTexto(nome, conteudo) {
  const blob = new Blob([conteudo], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = nome;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function debounce(fn, ms) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}

// ---------------------------------------------------------------------
// NAVEGAÇÃO ENTRE TELAS
// ---------------------------------------------------------------------

function mudarVista(nome) {
  document.querySelectorAll('.aba').forEach(b => b.classList.toggle('ativa', b.dataset.vista === nome));
  document.querySelectorAll('.vista').forEach(v => v.classList.toggle('ativa', v.id === 'vista-' + nome));

  if (nome === 'painel') carregarPainel();
  if (nome === 'biblioteca') carregarBiblioteca();
  if (nome === 'repertorio') carregarRepertorio();
  if (nome === 'backup') carregarStatusDrive();
}

// ---------------------------------------------------------------------
// PAINEL (DASHBOARD)
// ---------------------------------------------------------------------

async function carregarPainel() {
  await carregarPerfil();
  const dados = await api('/api/estatisticas');

  const horas = (dados.total_minutos / 60).toFixed(1);
  document.getElementById('stamps-estatisticas').innerHTML = `
    <div class="carimbo-stat"><div class="numero">${horas}h</div><div class="rotulo">Horas totais</div></div>
    <div class="carimbo-stat"><div class="numero">${dados.total_midias}</div><div class="rotulo">Mídias na biblioteca</div></div>
    <div class="carimbo-stat"><div class="numero">${dados.total_concluidas}</div><div class="rotulo">Concluídas</div></div>
    <div class="carimbo-stat"><div class="numero">${dados.total_idiomas}</div><div class="rotulo">Idiomas em imersão</div></div>
  `;

  if (graficoIdiomas) graficoIdiomas.destroy();
  graficoIdiomas = new Chart(document.getElementById('grafico-idiomas'), {
    type: 'bar',
    data: {
      labels: dados.por_idioma.map(r => r.idioma),
      datasets: [{
        label: 'Horas',
        data: dados.por_idioma.map(r => +(r.minutos / 60).toFixed(1)),
        backgroundColor: dados.por_idioma.map(r => corIdioma(r.idioma)),
        borderRadius: 4,
      }],
    },
    options: {
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true } },
    },
  });

  if (graficoTipos) graficoTipos.destroy();
  graficoTipos = new Chart(document.getElementById('grafico-tipos'), {
    type: 'doughnut',
    data: {
      labels: dados.por_tipo.map(r => r.tipo),
      datasets: [{
        data: dados.por_tipo.map(r => r.total),
        backgroundColor: ['#1B2A4A', '#A63A34', '#3F5B4D', '#B08D3E', '#6B4E71', '#B0562C', '#8A8272', '#57534A', '#7A9CC6', '#D6A24C', '#4E7C6B', '#C48A9E'],
      }],
    },
    options: { plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } } } },
  });

  const diasMapa = {};
  const hoje = new Date();
  for (let i = 6; i >= 0; i--) {
    const d = new Date(hoje);
    d.setDate(hoje.getDate() - i);
    diasMapa[dataLocalISO(d)] = 0;
  }
  dados.ultimos_dias.forEach(r => { if (r.data in diasMapa) diasMapa[r.data] = r.minutos; });

  if (graficoSemana) graficoSemana.destroy();
  graficoSemana = new Chart(document.getElementById('grafico-semana'), {
    type: 'bar',
    data: {
      labels: Object.keys(diasMapa).map(formatarDataCurta),
      datasets: [{ label: 'Minutos', data: Object.values(diasMapa), backgroundColor: '#1B2A4A', borderRadius: 4 }],
    },
    options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } },
  });

  renderizarDetalhamentoIdioma(dados.detalhamento_idioma || []);
  carregarHeatmap();
}

function renderizarDetalhamentoIdioma(detalhamento) {
  const tbody = document.querySelector('#tabela-detalhamento-idioma tbody');
  if (!detalhamento.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="obs">Nenhum dado ainda.</td></tr>';
    return;
  }
  tbody.innerHTML = detalhamento.map(d => `
    <tr>
      <td><span class="tag-idioma" style="background:${corIdioma(d.idioma)}">${escapeHtml(d.idioma)}</span></td>
      <td>${(d.minutos / 60).toFixed(1)}h</td>
      <td>${d.midias}</td>
      <td>${d.episodios || '—'}</td>
      <td>${d.paginas || '—'}</td>
      <td>${d.palavras || '—'}</td>
    </tr>
  `).join('');
}

function nivelHeatmap(minutos) {
  if (minutos <= 0) return 'nivel-0';
  if (minutos <= 20) return 'nivel-1';
  if (minutos <= 45) return 'nivel-2';
  if (minutos <= 90) return 'nivel-3';
  return 'nivel-4';
}

async function carregarHeatmap() {
  const dados = await api('/api/atividades/heatmap?dias=364');
  const mapa = {};
  dados.forEach(d => { mapa[d.data] = d.minutos; });

  const hoje = new Date();
  const dias = [];
  for (let i = 363; i >= 0; i--) {
    const d = new Date(hoje);
    d.setDate(hoje.getDate() - i);
    const chave = dataLocalISO(d);
    dias.push({ data: chave, minutos: mapa[chave] || 0 });
  }

  const container = document.getElementById('heatmap-container');
  container.innerHTML = dias.map(d => `
    <div class="heatmap-dia ${nivelHeatmap(d.minutos)}" title="${formatarDataCurta(d.data)}: ${d.minutos} min"></div>
  `).join('');
}

// ---------------------------------------------------------------------
// BIBLIOTECA (CRUD DE MÍDIAS)
// ---------------------------------------------------------------------

async function carregarBiblioteca() {
  await preencherFiltroIdiomas();

  const params = new URLSearchParams();
  const busca = document.getElementById('filtro-busca').value.trim();
  const idioma = document.getElementById('filtro-idioma').value;
  const tipo = document.getElementById('filtro-tipo').value;
  const status = document.getElementById('filtro-status').value;
  const ordenar = document.getElementById('filtro-ordenar').value;
  if (busca) params.set('busca', busca);
  if (idioma) params.set('idioma', idioma);
  if (tipo) params.set('tipo', tipo);
  if (status) params.set('status', status);
  if (ordenar) params.set('ordenar', ordenar);

  const midias = await api('/api/midias?' + params.toString());
  renderizarMidias(midias);
}

function renderizarMidias(midias) {
  const grade = document.getElementById('grade-midias');
  if (midias.length === 0) {
    grade.innerHTML = `<div class="vazio" style="grid-column:1/-1;"><strong>Nada por aqui ainda</strong>Adicione sua primeira mídia com o botão "+ Nova mídia".</div>`;
    return;
  }
  grade.innerHTML = midias.map(m => `
    <div class="ficha">
      ${m.repertorio ? '<span class="marca-repertorio">REPERTÓRIO</span>' : ''}
      <div class="ficha-topo">
        <span class="codigo-tipo">${m.tipo.toUpperCase()}</span>
        <span class="tag-idioma" style="background:${corIdioma(m.idioma)}">${escapeHtml(m.idioma)}</span>
      </div>
      ${m.capa_url
        ? `<img class="capa-ficha" src="${m.capa_url}" alt="" onerror="this.replaceWith(Object.assign(document.createElement('div'),{className:'capa-ficha capa-ausente'}))">`
        : '<div class="capa-ficha capa-ausente"></div>'}
      <h3>${escapeHtml(m.titulo)}</h3>
      ${m.progresso ? `<div class="progresso">${escapeHtml(m.progresso)}</div>` : ''}
      <span class="selo-status ${STATUS_CLASSE[m.status] || ''}">${escapeHtml(m.status)}</span>
      ${m.nota ? `<div class="estrelas">${formatarEstrelas(m.nota)}</div>` : ''}
      <div class="ficha-rodape">
        <button class="link-acao" onclick="abrirDetalhe(${m.id})">Sessões</button>
        <button class="link-acao" onclick="abrirModalEditar(${m.id})">Editar</button>
        <button class="link-acao apagar" onclick="apagarMidia(${m.id})">Apagar</button>
      </div>
    </div>
  `).join('');
}

async function preencherFiltroIdiomas() {
  const idiomas = await api('/api/idiomas');

  const select = document.getElementById('filtro-idioma');
  const valorAtual = select.value;
  select.innerHTML = '<option value="">Todos os idiomas</option>' +
    idiomas.map(i => `<option value="${escapeHtml(i)}">${escapeHtml(i)}</option>`).join('');
  select.value = valorAtual;

  const datalist = document.getElementById('lista-idiomas');
  const combinados = Array.from(new Set([...IDIOMAS_SUGERIDOS, ...idiomas]));
  datalist.innerHTML = combinados.map(i => `<option value="${escapeHtml(i)}">`).join('');
}

function preencherSelectsFormulario() {
  document.getElementById('midia-tipo').innerHTML = TIPOS.map(t => `<option value="${t}">${t}</option>`).join('');
  document.getElementById('midia-status').innerHTML = STATUS.map(s => `<option value="${s}">${s}</option>`).join('');
}

function preencherFiltrosFixos() {
  document.getElementById('filtro-tipo').innerHTML = '<option value="">Todos os tipos</option>' +
    TIPOS.map(t => `<option value="${t}">${t}</option>`).join('');
  document.getElementById('filtro-status').innerHTML = '<option value="">Todos os status</option>' +
    STATUS.map(s => `<option value="${s}">${s}</option>`).join('');
}

function limparPainelBusca() {
  document.getElementById('busca-status').textContent = '';
  document.getElementById('busca-status').className = 'busca-status';
  document.getElementById('busca-resultados').innerHTML = '';
}

function abrirModalNova() {
  document.getElementById('form-midia').reset();
  document.getElementById('midia-id').value = '';
  document.getElementById('modal-midia-titulo').textContent = 'Nova mídia';
  document.getElementById('campo-tema').style.display = 'none';
  limparPainelBusca();
  definirNotaSeletor(null);
  document.getElementById('modal-midia-fundo').classList.add('ativo');
}

// ---------- Seletor de nota (estrelas clicáveis, com suporte a meia-estrela) ----------

function definirNotaSeletor(nota) {
  const seletor = document.getElementById('seletor-nota');
  const input = document.getElementById('midia-nota');
  input.value = nota || '';
  seletor.dataset.valor = nota || '';

  const valor = nota ? Math.round(nota * 2) / 2 : 0;
  seletor.querySelectorAll('.estrela-input').forEach(estrela => {
    const posicao = Number(estrela.dataset.posicao);
    estrela.classList.remove('cheia', 'metade');
    if (valor >= posicao) {
      estrela.classList.add('cheia');
    } else if (valor >= posicao - 0.5) {
      estrela.classList.add('metade');
    }
  });
}

function inicializarSeletorNota() {
  const seletor = document.getElementById('seletor-nota');
  if (!seletor) return;

  seletor.querySelectorAll('.estrela-input').forEach(estrela => {
    // Clicar na metade esquerda da estrela = meia nota; metade direita = nota cheia.
    estrela.addEventListener('click', (evento) => {
      const posicao = Number(estrela.dataset.posicao);
      const retangulo = estrela.getBoundingClientRect();
      const cliqueNaMetadeEsquerda = (evento.clientX - retangulo.left) < retangulo.width / 2;
      const novaNota = cliqueNaMetadeEsquerda ? posicao - 0.5 : posicao;
      definirNotaSeletor(novaNota);
    });
  });

  document.getElementById('limpar-nota').addEventListener('click', () => definirNotaSeletor(null));
}

async function abrirModalEditar(id) {
  const m = await api(`/api/midias/${id}`);
  document.getElementById('midia-id').value = m.id;
  document.getElementById('midia-titulo').value = m.titulo;
  document.getElementById('midia-tipo').value = m.tipo;
  document.getElementById('midia-idioma').value = m.idioma;
  document.getElementById('midia-status').value = m.status;
  definirNotaSeletor(m.nota || null);
  document.getElementById('midia-progresso').value = m.progresso || '';
  document.getElementById('midia-capa').value = m.capa_url || '';
  document.getElementById('midia-repertorio').checked = !!m.repertorio;
  document.getElementById('midia-tema').value = m.tema_repertorio || '';
  document.getElementById('midia-anotacoes').value = m.anotacoes || '';
  document.getElementById('campo-tema').style.display = m.repertorio ? 'block' : 'none';
  document.getElementById('modal-midia-titulo').textContent = 'Editar mídia';
  limparPainelBusca();
  document.getElementById('modal-midia-fundo').classList.add('ativo');
}

function fecharModalMidia() {
  document.getElementById('modal-midia-fundo').classList.remove('ativo');
}

async function salvarMidia(evento) {
  evento.preventDefault();
  const id = document.getElementById('midia-id').value;
  const corpo = {
    titulo: document.getElementById('midia-titulo').value,
    tipo: document.getElementById('midia-tipo').value,
    idioma: document.getElementById('midia-idioma').value,
    status: document.getElementById('midia-status').value,
    nota: document.getElementById('midia-nota').value ? Number(document.getElementById('midia-nota').value) : null,
    progresso: document.getElementById('midia-progresso').value,
    capa_url: document.getElementById('midia-capa').value,
    repertorio: document.getElementById('midia-repertorio').checked,
    tema_repertorio: document.getElementById('midia-tema').value,
    anotacoes: document.getElementById('midia-anotacoes').value,
  };

  try {
    if (id) {
      await api(`/api/midias/${id}`, { method: 'PUT', body: JSON.stringify(corpo) });
    } else {
      await api('/api/midias', { method: 'POST', body: JSON.stringify(corpo) });
    }
    fecharModalMidia();
    carregarBiblioteca();
  } catch (erro) {
    alert('Não foi possível salvar: ' + erro.message);
  }
}

// ---------------------------------------------------------------------
// BUSCA AUTOMÁTICA DE METADADOS (capa, ano, sinopse)
// ---------------------------------------------------------------------

async function buscarMetadadosForm() {
  const tipo = document.getElementById('midia-tipo').value;
  const query = document.getElementById('midia-titulo').value.trim();
  const statusEl = document.getElementById('busca-status');
  const resultadosEl = document.getElementById('busca-resultados');
  resultadosEl.innerHTML = '';

  if (!query) {
    statusEl.textContent = 'Digite um título para buscar.';
    statusEl.className = 'busca-status erro';
    return;
  }
  if (TIPOS_SEM_BUSCA.includes(tipo)) {
    statusEl.textContent = `Não existe busca automática para o tipo "${tipo}". Preencha manualmente.`;
    statusEl.className = 'busca-status erro';
    return;
  }

  statusEl.textContent = 'Buscando...';
  statusEl.className = 'busca-status';

  try {
    const resultados = await api(`/api/buscar-metadados?tipo=${encodeURIComponent(tipo)}&q=${encodeURIComponent(query)}`);
    if (!resultados.length) {
      statusEl.textContent = 'Nenhum resultado encontrado. Tente outro termo, ou preencha manualmente.';
      return;
    }
    statusEl.textContent = `${resultados.length} resultado(s) — clique em um para preencher o formulário:`;
    resultadosEl.innerHTML = resultados.map((r, i) => `
      <div class="resultado-busca" data-indice="${i}">
        <img src="${r.capa_url || ''}" onerror="this.style.visibility='hidden'" alt="">
        <div class="titulo-resultado">${escapeHtml(r.titulo || '(sem título)')}</div>
        <div class="meta-resultado">${r.ano || ''} · ${r.fonte}</div>
      </div>
    `).join('');
    resultadosEl.querySelectorAll('.resultado-busca').forEach(el => {
      el.addEventListener('click', () => aplicarResultadoBusca(resultados[Number(el.dataset.indice)]));
    });
  } catch (erro) {
    statusEl.textContent = erro.message;
    statusEl.className = 'busca-status erro';
  }
}

function aplicarResultadoBusca(resultado) {
  if (resultado.titulo) document.getElementById('midia-titulo').value = resultado.titulo;
  if (resultado.capa_url) document.getElementById('midia-capa').value = resultado.capa_url;
  if (resultado.descricao) {
    const campoAnotacoes = document.getElementById('midia-anotacoes');
    if (!campoAnotacoes.value.trim()) campoAnotacoes.value = resultado.descricao;
  }
  document.getElementById('busca-status').textContent = 'Preenchido! Revise os campos antes de salvar.';
  document.getElementById('busca-resultados').innerHTML = '';
}

async function apagarMidia(id) {
  if (!confirm('Apagar esta mídia e todo o histórico de sessões dela?')) return;
  await api(`/api/midias/${id}`, { method: 'DELETE' });
  carregarBiblioteca();
}

// ---------------------------------------------------------------------
// DETALHE DA MÍDIA / REGISTRO DE SESSÕES DE IMERSÃO
// ---------------------------------------------------------------------

async function abrirDetalhe(id) {
  const m = await api(`/api/midias/${id}`);
  midiaDetalheAtual = id;
  tipoMidiaAtual = m.tipo;
  document.getElementById('detalhe-titulo').textContent = m.titulo;
  renderizarAtividades(m.atividades);
  document.getElementById('sessao-data').value = dataLocalISO(new Date());
  document.getElementById('sessao-minutos').value = '';
  document.getElementById('sessao-quantidade').value = '';
  document.getElementById('sessao-paginas').value = '';
  document.getElementById('sessao-palavras').value = '';

  const campoQtd = document.getElementById('campo-sessao-quantidade');
  const campoPaginas = document.getElementById('campo-sessao-paginas');
  const campoPalavras = document.getElementById('campo-sessao-palavras');

  campoQtd.style.display = 'none';
  campoPaginas.style.display = 'none';
  campoPalavras.style.display = 'none';

  if (TIPOS_EPISODIOS.includes(m.tipo)) {
    // Série, Anime: um único campo, em episódios.
    campoQtd.style.display = 'block';
    document.getElementById('rotulo-sessao-quantidade').textContent = 'Episódios';
  } else if (TIPOS_PAGINAS_E_PALAVRAS.includes(m.tipo)) {
    // Livro, Mangá, HQ, Novel: os dois campos aparecem juntos, cada um
    // pode ser preenchido independente do outro.
    campoPaginas.style.display = 'block';
    campoPalavras.style.display = 'block';
  } else if (TIPOS_SO_PALAVRAS.includes(m.tipo)) {
    // Visual Novel: só o campo de palavras, sem o de páginas.
    campoPalavras.style.display = 'block';
  }

  document.getElementById('modal-detalhe-fundo').classList.add('ativo');
}

function renderizarAtividades(atividades) {
  const lista = document.getElementById('lista-atividades');
  if (!atividades.length) {
    lista.innerHTML = '<p class="obs">Nenhuma sessão registrada ainda.</p>';
    return;
  }
  lista.innerHTML = atividades.map(a => {
    const partes = [];
    if (a.quantidade) partes.push(`${a.quantidade} episódios`);
    if (a.paginas) partes.push(`${a.paginas} páginas`);
    if (a.palavras) partes.push(`${a.palavras} palavras`);
    const extra = partes.length ? ` · ${partes.join(' · ')}` : '';
    return `
    <div class="item-atividade">
      <span>${formatarDataCurta(a.data)} — ${a.minutos} min${extra} ${a.observacao ? `<span class="obs">(${escapeHtml(a.observacao)})</span>` : ''}</span>
      <button class="link-acao apagar" onclick="apagarAtividade(${a.id})">Apagar</button>
    </div>
  `;
  }).join('');
}

async function registrarSessao() {
  const data = document.getElementById('sessao-data').value;
  const minutos = document.getElementById('sessao-minutos').value;
  const quantidade = document.getElementById('sessao-quantidade').value;
  const paginas = document.getElementById('sessao-paginas').value;
  const palavras = document.getElementById('sessao-palavras').value;
  if (!data || !minutos) { alert('Preencha data e minutos.'); return; }

  const corpo = { data, minutos: Number(minutos) };
  if (quantidade) corpo.quantidade = Number(quantidade);
  if (paginas) corpo.paginas = Number(paginas);
  if (palavras) corpo.palavras = Number(palavras);

  await api(`/api/midias/${midiaDetalheAtual}/atividades`, {
    method: 'POST',
    body: JSON.stringify(corpo),
  });
  const m = await api(`/api/midias/${midiaDetalheAtual}`);
  renderizarAtividades(m.atividades);
  document.getElementById('sessao-minutos').value = '';
  document.getElementById('sessao-quantidade').value = '';
  document.getElementById('sessao-paginas').value = '';
  document.getElementById('sessao-palavras').value = '';
  carregarBiblioteca();
}

async function apagarAtividade(id) {
  await api(`/api/atividades/${id}`, { method: 'DELETE' });
  const m = await api(`/api/midias/${midiaDetalheAtual}`);
  renderizarAtividades(m.atividades);
}

// ---------------------------------------------------------------------
// REPERTÓRIO SOCIOCULTURAL
// ---------------------------------------------------------------------

function agruparPorTema(midias) {
  const grupos = {};
  midias.forEach(m => {
    const tema = (m.tema_repertorio || '').trim() || 'Sem tema definido';
    if (!grupos[tema]) grupos[tema] = [];
    grupos[tema].push(m);
  });
  return grupos;
}

async function carregarRepertorio() {
  const midias = await api('/api/midias?repertorio=1');
  const container = document.getElementById('lista-repertorio');

  if (!midias.length) {
    container.innerHTML = `<div class="vazio"><strong>Nenhum repertório ainda</strong>Marque uma mídia como "repertório sociocultural" na Biblioteca para vê-la aqui.</div>`;
    return;
  }

  const grupos = agruparPorTema(midias);
  container.innerHTML = Object.entries(grupos).map(([tema, itens]) => `
    <div class="grupo-tema">
      <h3>${escapeHtml(tema)}</h3>
      ${itens.map(m => `
        <div class="cartao-repertorio">
          <h4>${escapeHtml(m.titulo)}</h4>
          <div class="meta">${escapeHtml(m.tipo)} · ${escapeHtml(m.idioma)}</div>
          ${m.anotacoes ? `<div class="anotacoes">${escapeHtml(m.anotacoes)}</div>` : '<div class="anotacoes obs">Sem anotações ainda.</div>'}
        </div>
      `).join('')}
    </div>
  `).join('');
}

async function exportarRepertorioTexto() {
  const midias = await api('/api/midias?repertorio=1');
  const grupos = agruparPorTema(midias);

  let texto = 'REPERTÓRIO SOCIOCULTURAL — Passaporte Cultural\n\n';
  Object.entries(grupos).forEach(([tema, itens]) => {
    texto += `## ${tema.toUpperCase()}\n`;
    itens.forEach(m => {
      texto += `- ${m.titulo} (${m.tipo}, ${m.idioma})\n`;
      if (m.anotacoes) texto += `  ${m.anotacoes.replace(/\n/g, '\n  ')}\n`;
    });
    texto += '\n';
  });

  baixarArquivoTexto('repertorio-sociocultural.txt', texto);
}

// ---------------------------------------------------------------------
// BACKUP
// ---------------------------------------------------------------------

function exportarBackup() {
  window.location.href = '/api/backup/exportar';
}

async function importarBackup(evento) {
  const arquivo = evento.target.files[0];
  if (!arquivo) return;

  if (!confirm('Isso vai substituir todos os dados atuais pelo conteúdo do backup. Continuar?')) {
    evento.target.value = '';
    return;
  }

  try {
    const texto = await arquivo.text();
    const dados = JSON.parse(texto);
    const resultado = await api('/api/backup/importar', { method: 'POST', body: JSON.stringify(dados) });
    alert(`Backup importado: ${resultado.midias_importadas} mídias, ${resultado.atividades_importadas} sessões.`);
  } catch (erro) {
    alert('Não foi possível importar: ' + erro.message);
  } finally {
    evento.target.value = '';
  }
}

// ---------------------------------------------------------------------
// GOOGLE DRIVE (sincronização opcional)
// ---------------------------------------------------------------------

async function carregarStatusDrive() {
  const statusEl = document.getElementById('drive-status');
  const acoesEl = document.getElementById('drive-acoes');
  try {
    const resultado = await api('/api/drive/status');
    if (resultado.configurado) {
      statusEl.textContent = '✓ Conectado ao Google Drive.';
      statusEl.className = 'drive-status';
      acoesEl.style.display = 'flex';
    } else {
      statusEl.textContent = 'Ainda não conectado. Veja o passo a passo no README (seção Google Drive).';
      statusEl.className = 'drive-status nao-configurado';
      acoesEl.style.display = 'none';
    }
  } catch (erro) {
    statusEl.textContent = 'Não foi possível checar o status do Google Drive.';
    statusEl.className = 'drive-status nao-configurado';
    acoesEl.style.display = 'none';
  }
}

async function enviarParaDrive() {
  try {
    await api('/api/drive/enviar', { method: 'POST' });
    alert('Backup enviado para o Google Drive com sucesso!');
  } catch (erro) {
    alert('Não foi possível enviar: ' + erro.message);
  }
}

async function baixarDoDrive() {
  if (!confirm('Isso vai substituir todos os dados atuais pelo backup salvo no Google Drive. Continuar?')) return;
  try {
    const resultado = await api('/api/drive/baixar', { method: 'POST' });
    alert(`Backup restaurado: ${resultado.midias_importadas} mídias, ${resultado.atividades_importadas} sessões.`);
    carregarBiblioteca();
  } catch (erro) {
    alert('Não foi possível baixar: ' + erro.message);
  }
}

// ---------------------------------------------------------------------
// CABEÇALHO (FOTO + NOME) E FILMES FAVORITOS (TOP 4)
// ---------------------------------------------------------------------

let perfilAtual = null;

async function carregarPerfil() {
  try {
    perfilAtual = await api('/api/perfil');
    renderizarPerfil(perfilAtual);
    renderizarTop4(perfilAtual.top4_detalhados || []);
  } catch (erro) {
    console.error('Erro ao carregar perfil:', erro);
  }
}

function renderizarPerfil(perfil) {
  // Elementos podem não existir se o perfil foi removido do Painel — usa guards
  const nomeEl = document.getElementById('perfil-nome-exibicao');
  if (nomeEl) nomeEl.textContent = perfil.nome || 'Viajante Cultural';

  const imgAvatar = document.getElementById('perfil-avatar-img');
  if (imgAvatar) {
    imgAvatar.src = perfil.avatar_url || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=300&auto=format&fit=crop&q=80';
  }
}

function renderizarTop4(top4List) {
  const container = document.getElementById('top4-posters-grid');
  let html = '';

  // Renderiza até 4 slots de pôsteres verticais
  for (let i = 0; i < 4; i++) {
    const item = top4List[i];

    if (item && (item.capa_url || item.titulo)) {
      const titulo = escapeHtml(item.titulo || 'Filme Favorito');
      const capa = item.capa_url || '';
      const nota = item.nota ? formatarEstrelas(item.nota) : '';

      html += `
        <div class="top4-poster-item" onclick="abrirModalTop4()">
          ${capa 
            ? `<img src="${escapeHtml(capa)}" alt="${titulo}" class="top4-poster-img" onerror="this.src='https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=300&auto=format&fit=crop&q=80'">`
            : `<div class="capa-ficha capa-ausente" style="height:100%;"></div>`
          }
          <div class="top4-overlay">
            <div class="top4-overlay-titulo">${titulo}</div>
            <div class="top4-overlay-meta">${item.tipo || 'Filme'} ${nota ? '· ' + nota : ''}</div>
          </div>
        </div>
      `;
    } else {
      // Slot vazio interativo para escolher filme
      html += `
        <div class="top4-slot-vazio" onclick="abrirModalTop4()">
          <span class="icone-plus">+</span>
          <span>Selecionar</span>
        </div>
      `;
    }
  }

  container.innerHTML = html;
}

// Manipulação do Modal de Editar Perfil (Nome e Foto)
function abrirModalPerfil() {
  if (!perfilAtual) return;
  document.getElementById('edit-perfil-nome').value = perfilAtual.nome || '';
  document.getElementById('edit-perfil-avatar').value = perfilAtual.avatar_url || '';
  document.getElementById('modal-perfil-fundo').classList.add('ativo');
}

function fecharModalPerfil() {
  document.getElementById('modal-perfil-fundo').classList.remove('ativo');
}

async function salvarPerfil(evento) {
  evento.preventDefault();
  const corpo = {
    nome: document.getElementById('edit-perfil-nome').value,
    avatar_url: document.getElementById('edit-perfil-avatar').value,
    top4_midias: perfilAtual ? perfilAtual.top4_midias : '[]'
  };

  try {
    await api('/api/perfil', { method: 'PUT', body: JSON.stringify(corpo) });
    fecharModalPerfil();
    carregarPerfil();
  } catch (erro) {
    alert('Erro ao salvar perfil: ' + erro.message);
  }
}

// Manipulação do Modal de Top 4 Filmes
async function abrirModalTop4() {
  const midias = await api('/api/midias');
  
  let top4Atual = [];
  try {
    top4Atual = typeof perfilAtual.top4_midias === 'string' ? JSON.parse(perfilAtual.top4_midias) : (perfilAtual.top4_midias || []);
  } catch (e) {
    top4Atual = [];
  }

  for (let i = 0; i < 4; i++) {
    const select = document.getElementById(`select-top4-slot-${i}`);
    select.innerHTML = '<option value="">-- Nenhum selecionado --</option>' +
      '<option value="custom">✏️ Outro filme (Personalizado)</option>' +
      midias.map(m => `<option value="${m.id}">${escapeHtml(m.titulo)} (${m.tipo})</option>`).join('');

    const val = top4Atual[i];
    const customDiv = document.getElementById(`custom-fields-${i}`);

    if (typeof val === 'number') {
      select.value = val;
      customDiv.style.display = 'none';
    } else if (typeof val === 'object' && val !== null) {
      select.value = 'custom';
      customDiv.style.display = 'block';
      document.getElementById(`top4-title-${i}`).value = val.titulo || '';
      document.getElementById(`top4-capa-${i}`).value = val.capa_url || '';
    } else {
      select.value = '';
      customDiv.style.display = 'none';
    }

    select.onchange = (e) => {
      customDiv.style.display = e.target.value === 'custom' ? 'block' : 'none';
    };
  }

  document.getElementById('modal-top4-fundo').classList.add('ativo');
}

function fecharModalTop4() {
  document.getElementById('modal-top4-fundo').classList.remove('ativo');
}

async function salvarTop4(evento) {
  evento.preventDefault();
  const novosTop4 = [];

  for (let i = 0; i < 4; i++) {
    const val = document.getElementById(`select-top4-slot-${i}`).value;
    if (!val) {
      novosTop4.push(null);
    } else if (val === 'custom') {
      const titulo = document.getElementById(`top4-title-${i}`).value.trim();
      const capa_url = document.getElementById(`top4-capa-${i}`).value.trim();
      if (titulo || capa_url) {
        novosTop4.push({ titulo: titulo || 'Filme Favorito', capa_url: capa_url, tipo: 'Filme' });
      } else {
        novosTop4.push(null);
      }
    } else {
      novosTop4.push(Number(val));
    }
  }

  try {
    const corpo = {
      ...perfilAtual,
      top4_midias: novosTop4
    };
    await api('/api/perfil', { method: 'PUT', body: JSON.stringify(corpo) });
    fecharModalTop4();
    carregarPerfil();
  } catch (erro) {
    alert('Erro ao salvar filmes favoritos: ' + erro.message);
  }
}

// ---------------------------------------------------------------------
// INICIALIZAÇÃO — conecta todos os botões e carrega a primeira tela
// ---------------------------------------------------------------------

function iniciar() {
  document.querySelectorAll('.aba').forEach(btn => btn.addEventListener('click', () => mudarVista(btn.dataset.vista)));

  document.querySelectorAll('.modal-fundo').forEach(fundo => {
    fundo.addEventListener('click', (e) => { if (e.target === fundo) fundo.classList.remove('ativo'); });
  });

  preencherSelectsFormulario();
  preencherFiltrosFixos();
  inicializarSeletorNota();

  // Listeners do Perfil (Foto/Nome) — usa ?. pois o botão de abrir pode não existir no HTML
  document.getElementById('btn-abrir-modal-perfil')?.addEventListener('click', abrirModalPerfil);
  document.getElementById('btn-cancelar-perfil')?.addEventListener('click', fecharModalPerfil);
  document.getElementById('form-perfil')?.addEventListener('submit', salvarPerfil);

  document.getElementById('btn-abrir-modal-top4').addEventListener('click', abrirModalTop4);
  document.getElementById('btn-cancelar-top4').addEventListener('click', fecharModalTop4);
  document.getElementById('form-top4').addEventListener('submit', salvarTop4);

  document.getElementById('btn-nova-midia').addEventListener('click', abrirModalNova);
  document.getElementById('btn-cancelar-midia').addEventListener('click', fecharModalMidia);
  document.getElementById('form-midia').addEventListener('submit', salvarMidia);
  document.getElementById('midia-repertorio').addEventListener('change', (e) => {
    document.getElementById('campo-tema').style.display = e.target.checked ? 'block' : 'none';
  });

  document.getElementById('filtro-busca').addEventListener('input', debounce(carregarBiblioteca, 300));
  document.getElementById('filtro-idioma').addEventListener('change', carregarBiblioteca);
  document.getElementById('filtro-tipo').addEventListener('change', carregarBiblioteca);
  document.getElementById('filtro-status').addEventListener('change', carregarBiblioteca);
  document.getElementById('filtro-ordenar').addEventListener('change', carregarBiblioteca);

  document.getElementById('btn-registrar-sessao').addEventListener('click', registrarSessao);
  document.getElementById('btn-fechar-detalhe').addEventListener('click', () => {
    document.getElementById('modal-detalhe-fundo').classList.remove('ativo');
  });

  document.getElementById('btn-exportar-repertorio').addEventListener('click', exportarRepertorioTexto);
  document.getElementById('btn-exportar-backup').addEventListener('click', exportarBackup);
  document.getElementById('input-importar-backup').addEventListener('change', importarBackup);

  document.getElementById('btn-buscar-metadados').addEventListener('click', buscarMetadadosForm);
  document.getElementById('btn-drive-enviar').addEventListener('click', enviarParaDrive);
  document.getElementById('btn-drive-baixar').addEventListener('click', baixarDoDrive);

  // Botão de alternância de tema claro/escuro
  document.getElementById('btn-toggle-tema').addEventListener('click', alternarTema);

  carregarPainel();
}

document.addEventListener('DOMContentLoaded', iniciar);

// =====================================================================
// TEMA CLARO / ESCURO
// A aplicação inicial fica no <head> do HTML (sem flash).
// Aqui só a função de toggle chamada pelo botão.
// =====================================================================

function alternarTema() {
  const html = document.documentElement;
  const temaAtual = html.getAttribute('data-theme');

  if (temaAtual === 'dark') {
    // Volta para o modo claro
    html.removeAttribute('data-theme');
    localStorage.setItem('passaporte-tema', 'light');
  } else {
    // Ativa o modo escuro
    html.setAttribute('data-theme', 'dark');
    localStorage.setItem('passaporte-tema', 'dark');
  }
}
