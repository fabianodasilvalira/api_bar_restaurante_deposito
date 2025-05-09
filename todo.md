# Lista de Tarefas - Correção API Restaurante

- [X] **Consolidar Configurações**
    - [X] Modificar `app/database.py` para importar `settings` de `app.core.config`.
    - [X] Modificar `app/auth.py` (o arquivo na raiz do diretório `app`) para importar `settings` de `app.core.config`.
- [X] **Limpeza de Arquivos Redundantes**
    - [X] Verificar se `app/config.py` se tornou obsoleto após as modificações e, em caso afirmativo, removê-lo.
- [ ] **Revisão Final e Validação**
    - [ ] Revisar `app/core/config.py` e `.env` para garantir que todas as configurações estão corretas e consistentes (Esta etapa de revisão inicial foi concluída. A variável `BACKEND_CORS_ORIGINS` em `app/core/config.py` está vazia, o que pode precisar de ajuste futuro dependendo dos requisitos de CORS da aplicação, mas não é um erro no momento).
    - [ ] Validar o funcionamento geral do projeto após todas as correções para garantir que não há erros de importação ou execução.
- [ ] **Backup e Entrega**
    - [ ] Criar um backup seguro (arquivo .zip) de todo o projeto corrigido.
    - [ ] Reportar todas as correções realizadas ao usuário de forma detalhada.
    - [ ] Enviar o arquivo de backup com o projeto corrigido ao usuário.
