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
		$__tasks
	\end{contest}
\end{document}
