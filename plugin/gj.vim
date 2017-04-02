"=============================================================================
" File: gj.vim
" Description: Instantly find out code symbols.
" Author: Chia-Hao Lo <fcamel@gmail.com>
" WebPage: http://github.com/fcamel/gj
" License: BSD
" Version: 0.7
" script type: plugin

if (exists('g:loaded_gj_vim') && g:loaded_gj_vim)
  finish
endif
let g:loaded_gj_vim = 1

let g:gjprg = expand("<sfile>:p:h") . "/../bin/gj_without_interaction"

function! s:Gj(cmd, args)
  redraw
  echo "Searching ..."

  let l:grepargs = a:args
  let grepprg_bak=&grepprg
  let grepformat_bak=&grepformat
  try
    let &grepprg=g:gjprg
    let &grepformat="%f:%l:%c:%m"
    silent execute a:cmd . " " . escape(l:grepargs, '|')
  finally
    let &grepprg=grepprg_bak
    let &grepformat=grepformat_bak
  endtry

  botright copen

  exec "nnoremap <silent> <buffer> q :ccl<CR>"
  exec "nnoremap <silent> <buffer> t <C-W><CR><C-W>T"
  exec "nnoremap <silent> <buffer> T <C-W><CR><C-W>TgT<C-W><C-W>"
  exec "nnoremap <silent> <buffer> o <CR>"
  exec "nnoremap <silent> <buffer> go <CR><C-W><C-W>"
  exec "nnoremap <silent> <buffer> h <C-W><CR><C-W>K"
  exec "nnoremap <silent> <buffer> H <C-W><CR><C-W>K<C-W>b"
  exec "nnoremap <silent> <buffer> v <C-W><CR><C-W>H<C-W>b<C-W>J<C-W>t"
  exec "nnoremap <silent> <buffer> gv <C-W><CR><C-W>H<C-W>b<C-W>J"

  redraw!
endfunction

command! -bang -nargs=* -complete=file Gj call s:Gj('grep<bang>', <q-args>)

"-----------------------------------------------------------------------------

" Find all occurence of the symbol under the cursor.
nnoremap <silent> <Leader>g :Gj! <C-R>=expand("<cword>")<CR> <CR>
" Find all possible declarations or definitions.
nnoremap <silent> <Leader>G :Gj! -d <C-R>=expand("<cword>")<CR> <CR>
" Find all possible definitions based on the debug info in ELF binaries.
" (much less results)
nnoremap <silent> <Leader>d :Gj! -D <C-R>=expand("<cword>")<CR> <CR>
