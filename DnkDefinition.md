# Компактное формальное определение $D_{n,k}$

## Область применимости и обозначения

Пусть

$$
n,k\in\mathbb{Z}_{\ge 0},
\qquad
n+k\ge 2,
\qquad
x,y\in\mathbb{Z}^{2}.
$$

Обозначения, используемые в автоматизированном поиске, связаны с
математическими обозначениями следующим образом:

$$
S_{1}\leftrightharpoons \mathtt{R1},
\qquad
D_{n,k}\leftrightharpoons \mathtt{R2}_{n,k}.
$$

Положим

$$
a\leftrightharpoons \min(n,k),
\qquad
b\leftrightharpoons \max(n,k).
$$

Тогда $0\le a\le b$ и $D_{n,k}=D_{a,b}$.

## Осевое отношение

Для каждого $\ell\in\mathbb{Z}_{\ge 0}$ определим вспомогательное осевое
отношение $A_{\ell}$ следующим образом:

$$
A_{\ell}(p,q)
\leftrightharpoons
\begin{cases}
p=q, & \ell=0,\\
S_{1}(p,q), & \ell=1,\\
D_{0,\ell}(p,q), & \ell\ge 2.
\end{cases}
$$

Таким образом, $A_{\ell}(p,q)$ означает, что точки $p$ и $q$ лежат на одной
координатной оси на расстоянии $\ell$ друг от друга.

## Прямолинейные цепочки

Пусть

$$
\boldsymbol{c}=(c_{1},\ldots,c_{s})
$$

--- конечный кортеж положительных целых чисел, и пусть

$$
\boldsymbol{p}=(p_{0},\ldots,p_{s})
$$

--- кортеж точек. Определим

$$
\operatorname{Straight}_{\boldsymbol{c}}(p_{0},\ldots,p_{s})
\leftrightharpoons
\left(
\bigwedge_{i=1}^{s} A_{c_i}(p_{i-1},p_i)
\right)
\land
\left(
\bigwedge_{i=1}^{s-1} A_{c_i+c_{i+1}}(p_{i-1},p_{i+1})
\right).
$$

Вторая конъюнкция состоит из перекрывающихся хорд. Она вынуждает соседние
отрезки лежать на одной координатной оси и иметь одинаковую ориентацию. При
$s=1$ вторая конъюнкция пуста и считается истинной.

## Каноническое разбиение длины

Для каждого положительного целого числа $L$ определим кортеж
$\operatorname{Split}(L)$ следующим образом:

$$
\operatorname{Split}(L)
\leftrightharpoons
\begin{cases}
(1), & L=1,\\
\left(
\operatorname{div}(L,2),
L-\operatorname{div}(L,2)
\right), & L\ge 2.
\end{cases}
$$

Во всех случаях элементы $\operatorname{Split}(L)$ положительны, а их сумма
равна $L$. При $L\ge 2$ каждый элемент разбиения строго меньше $L$.

Разбиение необходимо для рекурсивности определения. Если взять
$\boldsymbol{\alpha}=(a)$ и $\boldsymbol{\beta}=(b)$, то смешанное условие в
определении угла будет иметь вид $D_{a,b}(x,y)$ и окажется циклической ссылкой
на определяемое отношение. Разбиение хотя бы одной из длин на несколько
положительных частей заменяет эту ссылку отношением с меньшей суммой индексов.

## Перпендикулярная композиция двух прямолинейных цепочек

Пусть

$$
\boldsymbol{\alpha}=(\alpha_{1},\ldots,\alpha_{s}),
\qquad
\boldsymbol{\beta}=(\beta_{1},\ldots,\beta_{t})
$$

--- кортежи положительных целых чисел. Определим

$$
\begin{aligned}
\operatorname{Corner}_{\boldsymbol{\alpha},\boldsymbol{\beta}}(x,y)
\leftrightharpoons {}&
\exists p_{1},\ldots,p_{s-1},z,q_{1},\ldots,q_{t-1}\in\mathbb{Z}^{2}
\;\Bigl(
\operatorname{Straight}_{\boldsymbol{\alpha}}
(x,p_{1},\ldots,p_{s-1},z)
\\
&\land
\operatorname{Straight}_{\boldsymbol{\beta}}
(z,q_{1},\ldots,q_{t-1},y)
\land
D_{\alpha_{s},\beta_{1}}(p_{s-1},q_{1})
\Bigr).
\end{aligned}
$$

При $s=1$ список $p_1,\ldots,p_{s-1}$ отсутствует, первая цепочка имеет вид
$\operatorname{Straight}_{\boldsymbol{\alpha}}(x,z)$, а в смешанном отношении
полагается $p_{s-1}=x$. При $t=1$ список $q_1,\ldots,q_{t-1}$ отсутствует,
вторая цепочка имеет вид
$\operatorname{Straight}_{\boldsymbol{\beta}}(z,y)$, а в смешанном отношении
полагается $q_1=y$.

Смешанное отношение $D_{\alpha_s,\beta_1}(p_{s-1},q_1)$ вынуждает последний
отрезок первой прямолинейной цепочки и первый отрезок второй прямолинейной
цепочки быть перпендикулярными.

## Вспомогательные случаи

### Чётная осевая длина

Для чётного целого числа $b\ge 2$ положим

$$
q\leftrightharpoons \operatorname{div}(b,2)
$$

и определим

$$
\begin{aligned}
\operatorname{EvenAxis}_{b}(x,y)
\leftrightharpoons
\exists z\in\mathbb{Z}^{2}\;\Bigl(&
A_q(x,z)
\land A_q(z,y)
\\
&\land
\forall w\in\mathbb{Z}^{2}\;
\bigl(
(A_q(x,w)\land A_q(w,y))
\longrightarrow w=z
\bigr)
\Bigr).
\end{aligned}
$$

Таким образом, $z$ является единственной общей $A_q$-серединой точек $x$ и
$y$.

### Нечётная осевая длина

Для нечётного целого числа $b\ge 3$ положим

$$
q\leftrightharpoons \operatorname{div}(b,2),
\qquad
r\leftrightharpoons b-q,
$$

и определим

$$
\begin{aligned}
\operatorname{OddAxis}_{b}(x,y)
\leftrightharpoons
\exists z,w\in\mathbb{Z}^{2}\;\Bigl(&
A_r(x,z)
\land A_q(z,y)
\land A_q(x,w)
\\
&\land A_r(w,y)
\land S_1(z,w)
\Bigr).
\end{aligned}
$$

### Единичная диагональ

Определим

$$
\begin{aligned}
\operatorname{UnitDiagonal}(x,y)
\leftrightharpoons
{}&x\ne y
\land
\exists z,w\in\mathbb{Z}^{2}\;\Bigl(
z\ne w
\land S_1(x,z)
\land S_1(z,y)
\\
&\land S_1(x,w)
\land S_1(w,y)
\Bigr).
\end{aligned}
$$

## Компактное определение $D_{n,k}$

Для $n,k\in\mathbb{Z}_{\ge 0}$, удовлетворяющих $n+k\ge 2$, положим
$a\leftrightharpoons\min(n,k)$ и $b\leftrightharpoons\max(n,k)$. Тогда

$$
D_{n,k}(x,y)
\Leftrightarrow
\begin{cases}
\operatorname{EvenAxis}_{b}(x,y),
& a=0\land \operatorname{mod}(b,2)=0,\\
\operatorname{OddAxis}_{b}(x,y),
& a=0\land \operatorname{mod}(b,2)=1,\\
\operatorname{UnitDiagonal}(x,y),
& a=1\land b=1,\\
\operatorname{Corner}_{\operatorname{Split}(a),\operatorname{Split}(b)}(x,y),
& 1\le a\le b\land (a,b)\ne(1,1).
\end{cases}
$$

Эти четыре условия попарно несовместны и исчерпывают все пары неотрицательных
параметров, удовлетворяющие $n+k\ge 2$.

## Корректность рекурсивного определения

Компактное определение следует понимать как определение по сильной индукции по
$n+k$. Для каждого вхождения $D_{i,j}$ в правую часть выполнено

$$
i+j<n+k.
$$

В случаях чётной и нечётной осевой длины все осевые индексы строго меньше $b$.
В случае угла осевые индексы первой и второй цепочек не превосходят
соответственно $a$ и $b$, причём $a<a+b$ и $b<a+b$. Поскольку случай
$(a,b)=(1,1)$ выделен отдельно, имеем $b\ge 2$. Поэтому первый элемент
$\operatorname{Split}(b)$ строго меньше $b$. Для отношения в вершине угла
выполнено

$$
\alpha_s+\beta_1<a+b.
$$

Следовательно, компактная формула не создаёт циклической зависимости.

## Статус верификации

Это компактная семантическая формализация формулы из файла
`AutomatisationTests/output/generalised_formula.md`. В настоящей записи
технические разбиения generaliser упрощены, а отдельный случай малого
прямоугольника устранён. Автоматизированная проверка подтвердила исходную
развёрнутую формулу на всех 166 выбранных парах параметров при $0\le n,k\le 12$
и $2\le n+k\le 24$; данная упрощённая запись непосредственно в формате
проверяющей программы не запускалась.

Ограниченная верификация не является доказательством для неограниченной области.
В частности, случаи $n+k<2$ не входят в указанную область применимости, а для
проверки за пределами выбранной области необходимо иметь соответствующие
меньшие отношения $D_{i,j}$ в качестве верифицированных предшественников.
