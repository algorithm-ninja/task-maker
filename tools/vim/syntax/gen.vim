" Quit when a syntax file was already loaded.
if exists('b:current_syntax') | finish |  endif

syntax match GenName      /\w\+/ contained
syntax match GenExe       /[a-zA-Z0-9/.]\+/ contained
syntax match GenNameGV    /\w\+/ contained nextgroup=GenExe skipwhite
syntax match GenScore     /\d\+/ contained nextgroup=GenName skipwhite
syntax keyword GenGeneratorK contained GEN VAL nextgroup=GenNameGV skipwhite
syntax keyword GenRunK contained RUN nextgroup=GenName skipwhite
syntax keyword GenSubtaskK contained SUBTASK nextgroup=GenScore skipwhite
syntax keyword GenConstraintK contained CONSTRAINT nextgroup=GenNumber
syntax match GenCommand   /^:.*/ contains=GenGeneratorK,GenSubtaskK,GenConstraintK,GenRunK
syntax match GenComment   /^#.*/

hi def link GenComment Comment
hi def link GenScore Number
hi def link GenName Special
hi def link GenNameGV Special
hi def link GenCommand Statement
hi def link GenExe Macro
hi def link GenGeneratorK vimCommand
hi def link GenRunK vimCommand
hi def link GenSubtaskK vimCommand
hi def link GenConstraintK vimCommand

let b:current_syntax = 'gen'
