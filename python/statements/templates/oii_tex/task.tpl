\documentclass[%
	$__language,%
	$__showsolutions,%
	$__showsummary,%
]{cms-contest}

\usepackage[$fontenc]{fontenc}
\usepackage[$inputenc]{inputenc}
\usepackage[$__language]{babel}
\usepackage{bookmark}

$__packages

\begin{document}
	\begin{contest}{$description}{$location}{$date}
		\setContestLogo{$logo}
		\begin{problem}{$title}{$name}{$infile}{$outfile}{$time_limit}{$memory_limit}{$difficulty}{$syllabuslevel}
        $__content
        \end{problem}
	\end{contest}
\end{document}
