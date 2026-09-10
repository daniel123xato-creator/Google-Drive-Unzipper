# 📦 Descompactador Google Drive (macOS)

Ferramenta especializada para **macOS** projetada para descompactar e unificar arquivos particionados pelo **Google Drive** (como `Arquivo-001.zip`, `Arquivo-002.zip` ou `drive-download-*.zip`) em uma **única pasta raiz compartilhada**.

---

## 🎯 O Problema que este software resolve

Quando o Google Drive faz o download de pastas grandes, ele divide o arquivo em múltiplos volumes `.zip` (geralmente até 2GB cada). Ao descompactar pelo utilitário padrão do Mac (Archive Utility):
1. O macOS cria várias pastas separadas (`Arquivo-001/`, `Arquivo-002/`).
2. A estrutura de subpastas fica espalhada e fragmentada.
3. Mesclar manualmente pelo Finder é demorado e pode causar sobrescrita indesejada ou confusão com pastas de mesmo nome.

Com o **Descompactador Google Drive**, todos os arquivos de todas as partes são **combinados e organizados na mesma pasta raiz**, preservando perfeitamente a árvore de pastas original e limpando lixo de metadados.

---

## 🚀 Como Usar o Aplicativo Gráfico (App do Mac)

O executável nativo do Mac está pronto nesta pasta:
```text
Descompactador Drive.app
```

### Passo a passo:
1. **Abra o aplicativo**: Dê um duplo clique em `Descompactador Drive.app` (ou arraste-o para a pasta `/Applications` do seu Mac).
2. **Selecione os arquivos**:
   - Clique em **📄 Selecionar Arquivos .zip...** para selecionar os arquivos `.zip` do Drive de uma vez (você pode selecionar vários segurando `Shift` ou `Cmd`).
   - OU clique em **📁 Selecionar Pasta com Zips...** e escolha a pasta onde seus downloads foram salvos (o app detecta e organiza as partes `001`, `002`... automaticamente).
3. **Pasta Raiz de Destino**: O app sugere automaticamente uma pasta organizada com o nome original do conteúdo. Você pode alterá-la clicando em **Escolher...**.
4. **Opções Adicionais**:
   - ✅ *Limpar arquivos desnecessários (`__MACOSX`, `.DS_Store`)*: remove os arquivos de metadados invisíveis do sistema.
   - ✅ *Abrir pasta no Finder ao terminar*: abre a pasta finalizada assim que concluir.
   - ⬜ *Excluir arquivos .zip originais após extração*: se você precisa economizar espaço em disco, marque esta opção para apagar os zips baixados após a extração com sucesso.
5. **Clique em "🚀 Descompactar e Unificar Arquivos"**: Acompanhe o progresso em tempo real (velocidade em MB/s, percentual e arquivo atual). Ao terminar, a pasta unificada estará pronta no Finder!

---

## 💻 Uso via Linha de Comando (CLI / Terminal)

Se preferir rodar via Terminal ou automatizar em scripts:

```bash
# Descompactar informando arquivos individuais:
python3 core_unpacker.py Arquivo-001.zip Arquivo-002.zip Arquivo-003.zip -o "/Caminho/Da/Pasta/Destino"

# Descompactar apontando diretamente para a pasta com os zips:
python3 core_unpacker.py "/Users/seu-usuario/Downloads/PastaComZips" -o "/Users/seu-usuario/Desktop/Resultado"

# Opções adicionais:
# --delete-source : apaga os arquivos .zip originais após sucesso
# --keep-macosx   : mantém os arquivos __MACOSX se desejar
```

---

## 🧪 Teste de Integridade

Para validar o funcionamento do motor de unificação e filtragem:
```bash
python3 test_unpacker.py
```

---

## 🛠️ Como Recompilar o Aplicativo (.app)

Caso você queira personalizar ou recompilar o pacote do Mac:
```bash
python3 build_app.py
```
Isso gerará novamente o `Descompactador Drive.app` com os ícones de alta resolução e executável integrados.
