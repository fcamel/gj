# gj #

Usually we have two needs when reading codes:

* Find out the definition (or declaration) of `foo`. `foo` may be a class, method or a function.
* Find out all places which use `foo`.

`grep -R foo .` is good for the second case since it won't miss any direct use. However, `grep` is not
fast enough for large projects and it's somewhat inconvent for the first case. This is why [gj] is created.

The goals of [gj] from high to low are:

* Low miss: it's bad to miss a caller when you refactor codes or find out who modifies the target variable.
* Speed: list possible targets instantly.
* Less reading time: interactively narrow down to your target.

[gj] is used in two ways:

* Run as an interactive command line tool to edit and filter candidate files interactively.
* As a plugin in vim to find files which containt the symbol under the cursor.

## Installation ##

### Prerequisite ###

[gj] is based on [ID Utils] which finds symbols instantly.

Install [ID Utils] on Debian / Ubuntu with:

    sudo apt-get install id-utils

### Vim Plugin + Command Line tool ###

#### Vundle ####

Install [gj.vim] via [Vundle]. Please refer documents in [Vundle]: a highly recommended tool to manage vim plugins.

#### Vim plugins ####

[gj.vim] depends on [ack.vim], so you need to install [ack.vim], too. Add these to your `.vimrc`:

```vim
Bundle 'mileszs/ack.vim'
Bundle 'fcamel/gj'
```

Then launch `vim` and run `:BundleInstall`.

In order to use the command line tool, add this to your `~/.bashrc` (or other shell config file):

```bash
export PATH="$PATH:~/.vim/bundle/gj/bin"
```

### (optional) Command Line Tool only ###

```baseh
$ git clone https://github.com/fcamel/gj
$ mkdir ~/bin/
$ cp -p bin/* ~/bin/
$ export PATH="$PATH:~/bin"
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

[gj]:https://github.com/fcamel/gj
[gj.vim]:https://github.com/fcamel/gj/blob/master/plugin/gj.vim
[ID Utils]:http://www.gnu.org/software/idutils/
[Vundle]:http://github.com/gmarik/vundle
[ack.vim]:https://github.com/mileszs/ack.vim
