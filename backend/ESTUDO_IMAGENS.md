# Resumo para estudar amanhã — imagens das lojas

1. **Entrada:** `upload_image` em [routes.py](app/modules/stores/routes.py) recebe `file`, JWT e tipo `logo`/`cover`.
2. **Autorização:** `upload_image` em [image_service.py](app/modules/stores/image_service.py) consulta loja/vínculo e libera o banco antes do processamento e da rede.
3. **Validação:** `validate_store_image` em [image_processing.py](app/modules/stores/image_processing.py) verifica bytes, formato, tamanho, resolução e número de frames.
4. **Pillow:** `process_store_image` decodifica com `load()`. `ImageOps.exif_transpose()` corrige rotação/espelhamento antes do resize.
5. **Normalização/WebP:** converte ICC válido/compatível para sRGB e usa RGB ou RGBA, limpa metadados e salva WebP. Logo usa qualidade 90; cover, 85.
6. **Tamanhos:** `IMAGE_PRESETS` define logo 256/512 e cover 960/1920. `thumbnail(..., LANCZOS)` mantém proporção sem crop/upscale; tamanhos iguais compartilham arquivo.
7. **Supabase:** `upload_store_image` em [storage.py](app/modules/stores/storage.py) envia só as variantes, em pasta com UUID novo. A chave fica no backend.
8. **Banco:** [models.py](app/modules/stores/models.py) separa `StoreImage` (logo/cover) de `StoreImageVariant` (arquivo, tamanho e path).
9. **Substituição:** depois dos uploads, o service bloqueia a loja, revalida o vínculo e troca todas as variantes numa transação. Só após commit limpa os arquivos antigos.
10. **Erros:** antes do upload, nada vai ao Storage. Falhas parciais ou rejeição confirmada do banco limpam os novos arquivos; commit incerto preserva-os. `cleanup_store_images` tenta cada path uma vez e registra falhas.

As rotas continuam `PUT`/`DELETE /stores/{store_id}/images/{image_type}`. A resposta traz `variants`, com URL e metadados, sem paths internos. A migration `0004` preserva imagens anteriores do 3A; novos envios são processados.
