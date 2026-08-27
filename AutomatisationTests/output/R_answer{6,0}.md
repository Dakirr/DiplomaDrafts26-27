# Verified definition of `R2`

## Parameters

- `n`: fixed at `6`
- `k`: fixed at `0`

## Verified equivalence

$$
\mathtt{R2}_{\mathit{n},\mathit{k}}\left(\mathit{x},\mathit{y}\right) \Leftrightarrow \left(\exists \mathit{z}\in\mathbb{Z}^{2}\;\left(\mathtt{R1}\left(\mathit{x},\mathit{z}\right) \land \left(\mathtt{R2}_{\mathit{n}-6,\mathit{k}+5}\left(\mathit{z},\mathit{y}\right) \lor \mathtt{R2}_{\mathit{n}-5,\mathit{k}+4}\left(\mathit{z},\mathit{y}\right) \lor \mathtt{R2}_{\mathit{n}-4,\mathit{k}+3}\left(\mathit{z},\mathit{y}\right)\right) \land \left(\forall \mathit{w}\in\mathbb{Z}^{2}\;\left(\left(\mathtt{R1}\left(\mathit{x},\mathit{w}\right) \land \left(\mathtt{R2}_{\mathit{n}-6,\mathit{k}+5}\left(\mathit{w},\mathit{y}\right) \lor \mathtt{R2}_{\mathit{n}-5,\mathit{k}+4}\left(\mathit{w},\mathit{y}\right) \lor \mathtt{R2}_{\mathit{n}-4,\mathit{k}+3}\left(\mathit{w},\mathit{y}\right)\right)\right) \longrightarrow \left(\mathit{w} = \mathit{z}\right)\right)\right)\right)\right)
$$

## Candidate source

```text
(exists ((z Point)) (and (R1 x z) (or (R2__n_0__k_5 z y) (R2__n_1__k_4 z y) (R2__n_2__k_3 z y)) (forall ((w Point)) (=> (and (R1 x w) (or (R2__n_0__k_5 w y) (R2__n_1__k_4 w y) (R2__n_2__k_3 w y))) (= w z)))))
```
