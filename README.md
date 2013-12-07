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
* As a plugin in [Vim] to find files which containt the word under the cursor.

## Demo ##

![Example usage of gj](https://raw.github.com/fcamel/screenshots/master/gj/gj_demo.gif)

1. `gj -i`: build the index.
2. `gj main argc argv`: find out the main functions. C/C++ main() typically has these three keywords.
3. `example`: keep files with the substring *example* in the file name.
4. `!test`: remove files with the substring *test* in the file name.
5. `1`: Use [Vim] to edit the first file and jump to the corresponding line.
6. Exit [Vim] and back to [gj].
7. `2`: Edit the second one.
8. In [Vim], `<leader>G` under *DoLogin*: list possible definitions or declarations of *DoLogin*.
9. In [Vim], `<leader>g` under *DoLogin*: list all callers, definitions or declarations of *DoLogin*.

## Installation ##

### Prerequisite ###

[gj] is based on [ID Utils] which finds patterns instantly. Install [ID Utils] by:

```bash
$ sudo apt-get install id-utils  # Debian / Ubuntu
$ sudo port install idutils      # OS X with MacPorts
$ brew install idutils           # OS X with Homebrew
```

### Vim Plugin + Command Line Tool ###

#### Vundle ####

Install [gj.vim] via [Vundle]. Please refer documents in [Vundle]: a highly recommended tool to manage [Vim] plugins.

#### Vim plugins ####

[gj.vim] depends on [ack.vim], so you need to install [ack.vim], too. Add these to your `.vimrc`:

```vim
Bundle 'mileszs/ack.vim'
Bundle 'fcamel/gj'
```

Then launch `vim` and run `:BundleInstall`.

In order to use the command line tool, add this to your `$HOME/.bashrc` (or other shell config file):

```bash
export PATH="$PATH:$HOME/.vim/bundle/gj/bin"
```

### (optional) Command Line Tool Only ###

```bash
$ cd /path/to/somewhere/
$ git clone https://github.com/fcamel/gj
$ export PATH="$PATH:`pwd`/bin"
```

## Usage ##

### Command Line Tool ###

```bash
$ cd /path/to/project/
$ gj -i                 # Build the index.
$ gj PATTERN            # Find out PATTERN
```

Then follow the instructions in terminal. 

If you don't use [Vim] as your main editor, please set the environment variable `EDITOR` to your favorite editor.
However, currently only [Vim] supports "jump to the line" and "highlight the searched pattern" when opening
the file.

Other useful arguments:

```bash
$ gj -s LITERAL         # Show all symbols which contain LITERAL (case-insensitive)
$ gj -sv LITERAL        # Same as above, but also display file lists for each symbol.
$ gj -d1 PATTERN        # Try to find out PATTERN's definition or declaration. Work for C++ or Python.
```


### Vim Plugin ###

In Normal mode:

* `<leader>g`: Find all matched files of the word under the cursor.
* `<leader>G`: Find all possible declarations or definitions of the word under the cursor.
* `<leader>d`: Find all possible declarations or definitions with a more strongly guess (much less results) of the word under the cursor.

Then use the following commands in quickfix window:

* `o` : open file (same as enter).
* `go`: open file (but maintain focus in quickfix window). 
* `t` : open in a new tab.
* `T` : open in new tab silently.
* `h` : open in horizontal split.
* `H` : open in horizontal split silently.
* `v` : open in vertical split.
* `gv`: open in vertical split silently.
* `q` : close the quickfix window.


[gj]:https://github.com/fcamel/gj
[gj.vim]:https://github.com/fcamel/gj/blob/master/plugin/gj.vim
[Vim]:http://www.vim.org/
[ID Utils]:http://www.gnu.org/software/idutils/
[Vundle]:http://github.com/gmarik/vundle
[ack.vim]:https://github.com/mileszs/ack.vim

## Todo ##

* Improve `-d`'s speed.
* Improve `-d`'s accuracy.
* Support Emacs as well.
* Add more screenshots.
