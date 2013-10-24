# gj #

This is a front for [id-utils](http://www.gnu.org/software/idutils/) which finds symbols instantly.

There are two ways to use gj:

* Run as an interactive command line tool to edit and filter candidate files interactively.
* As a plugin in vim to find files which containt the symbol under the cursor.

## Installation ##

### id-utils ###

Install on Debian / Ubuntu with:

    sudo apt-get install id-utils

### The Vim Plugin ###

Install gj.vim via [Vundle]. gj.vim depends on [ack.vim], so you need to install [ack.vim] first. Add these to your `.vimrc`:

```vim
Bundle 'mileszs/ack.vim'
Bundle 'fcamel/gj'
```

Then launch `vim` and run `:BundleInstall`.

### Command Line Tool ###

After you installed the vim plugin via vundle, add this to your `~/.bashrc` (or other shell config file):

```bash
export PATH="$PATH:~/.vim/bundle/gj/bin"
```

## Usage ##

### Command Line Tool ###

TODO

```bash
$ cd /path/to/project/
$ mkid
$ gj SYMBOL
```

### Vim Plugin ###

TODO

In Vim:
```
<leader>g: Find all matched files of the symbol under the cursor.
<leader>G: Find all possible declarations or definitions of the symbol under the cursor.
<leader>d: Find all possible declarations or definitions with a more strongly guess (much less results) of the symbol under the cursor..
```


[Vundle]:http://github.com/gmarik/vundle
[ack.vim]:https://github.com/mileszs/ack.vim
