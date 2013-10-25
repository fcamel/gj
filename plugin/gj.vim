"=============================================================================
" File: gj.vim
" Description: Instantly find out code symbols.
" Author: Chia-Hao Lo <fcamel@gmail.com>
" WebPage: http://github.com/fcamel/gj
" License: BSD
" Version: 0.6
" script type: plugin

if (exists('g:loaded_gj_vim') && g:loaded_gj_vim)
  finish
endif
let g:loaded_gj_vim = 1

let g:ackprg = expand("<sfile>:p:h") . "/../bin/gj_without_interaction"

" Find all occurence of the symbol under the cursor.
nnoremap <silent> <Leader>g :Ack!<CR>
" Find all possible declarations or definitions.
nnoremap <silent> <Leader>G :Ack! -d1 <C-R>=expand("<cword>")<CR> <CR>
" Find all possible declarations or definitions with a more strongly guess
" (much less results)
nnoremap <silent> <Leader>d :Ack! -d2 <C-R>=expand("<cword>")<CR> <CR>
