import numpy as np
import matplotlib.pyplot as plt
from cvxopt import solvers, matrix
from .pla import PLA
from .dataset import PointsDataset


# Kernel functions
# All operations are performed on third dimention which is original feature dimention.
# All kernel functions receive two array-like paramters which have shape (n1, d) and (n2, d)
# and return one array-like result which has shape (n1, n2)
def linear_kernel():
    """
    form: <x, x_prime>
    """
    def f(x, x_prime):
        if x.ndim == 1:
            x = x[np.newaxis, :]
        if x_prime.ndim == 1:
            x_prime = x_prime[np.newaxis, :]
        assert x.shape[1] == x_prime.shape[1]  # must have the same dimention

        shape = (x.shape[0], x_prime.shape[0])
        x = x[:, np.newaxis, :]
        x_prime = x_prime[np.newaxis, :, :]
        return np.inner(x, x_prime).reshape(shape)
    return f


def poly_kernel(degree, gamma=1, coef=1):
    """
    form: (coef + gamma * <x, x_prime>) ** degree
    """
    def f(x, x_prime):
        if x.ndim == 1:
            x = x[np.newaxis, :]
        if x_prime.ndim == 1:
            x_prime = x_prime[np.newaxis, :]
        assert x.shape[1] == x_prime.shape[1]  # must have the same dimention

        shape = (x.shape[0], x_prime.shape[0])
        x = x[:, np.newaxis, :]
        x_prime = x_prime[np.newaxis, :, :]
        k = (np.inner(x, x_prime) * gamma + coef) ** degree
        return k.reshape(shape)
    return f


def rbf_kernel(gamma):
    """
    form: exp(-gamma * <x, x_prime>) ** 2
    """
    def f(x, x_prime):
        if x.ndim == 1:
            x = x[np.newaxis, :]
        if x_prime.ndim == 1:
            x_prime = x_prime[np.newaxis, :]
        assert x.shape[1] == x_prime.shape[1]  # must have the same dimention

        x = x[:, np.newaxis, :]
        x_prime = x_prime[np.newaxis, :, :]
        k = np.exp(-1 * gamma * ((x - x_prime) ** 2).sum(axis=2))
        return k
    return f


class SVM:
    """
    A support vector machine object.
    """
    def __init__(self, tol=1e-3, kernel=None):
        """
        tol: Tolerance that is criterion of determining wether an alpha is zero or not.
        """
        if kernel is None:
            kernel = linear_kernel()

        self.tol = tol
        self.kernel = kernel  # kernel function
        self.alphas, self.b = None, None
        self._X, self._y = None, None  # supports vectors
        self.supports = None  # index of support vectors

    def get_weight(self):
        raise NotImplementedError

    def get_supports(self):
        """
        Return the index of support vectors
        """
        return self.supports

    def get_support_vectors(self):
        """
        Return support vectors
        """
        return self._X

    def _estimate(self, x):
        """
        Compute the value of alpha * y * kernel
        """
        assert self.alphas is not None and self.supports is not None

        return ((self.alphas * self._y)[:, np.newaxis]
                * self.kernel(self._X, x)).sum(axis=0)

    def fit(self, X, y):
        """
        Fit the dataset
        """
        assert y.shape[0] == X.shape[0]

        y = y.reshape((-1, 1))  # force column vector
        n, d = X.shape

        Q = y.dot(y.T) * self.kernel(X, X)  # now much faster
        p = np.ones(n) * -1
        # alpha >= 0
        G = np.eye(n) * -1
        h = np.zeros(n)
        # alpha * y = 0
        A = y.T
        b = np.zeros(1)

        solvers.options['show_progress'] = False
        alphas = solvers.qp(matrix(Q, tc='d'), matrix(p), matrix(G),
                            matrix(h), matrix(A, tc='d'), matrix(b))['x']

        alphas = np.ravel(alphas)
        if np.all(alphas < self.tol):
            raise AssertionError('all alphas are zero.')
        self.supports = np.where(alphas > self.tol)[0]
        self.alphas = alphas[self.supports]
        self._X, self._y = X[self.supports], y[self.supports].ravel()
        m = self.supports[0]
        self.b = y[m] - self._estimate(X[m])

    def predict(self, X):
        """
        Predict the label.
        """
        return np.where(self._estimate(X) + self.b >= 0, 1, -1)

    def error(self, X, y):
        """
        Return the rate of misclassification.
        """
        predicted = self.predict(X)
        return 1 - (y == predicted).sum() / predicted.size

    def plot(self, X, y, ax=None):
        assert self.alphas is not None and self.supports is not None

        if ax is None:
            fig, ax = plt.subplots()

        # create a mesh to plot in
        h = .02  # step size
        x1_min, x1_max = X[:, 0].min() - 1, X[:, 0].max() + 1
        x2_min, x2_max = X[:, 1].min() - 1, X[:, 1].max() + 1
        x1x1, x2x2 = np.meshgrid(np.arange(x1_min, x1_max, h),
                                 np.arange(x2_min, x2_max, h))

        # plot boundary
        labels = self.predict(np.c_[x1x1.ravel(), x2x2.ravel()])
        ax.contourf(x1x1, x2x2, labels.reshape(x1x1.shape),
                    cmap=plt.cm.Paired, alpha=0.8)
        # plot data set
        plt.scatter(X[:, 0], X[:, 1], s=40, c=y, cmap=plt.cm.Paired)
        # plot support vectors
        # draw a square around each support vector
        square = {'marker': 's',
                  'facecolor': 'none',
                  'edgecolor': 'black',
                  's': 100}
        plt.scatter(self.get_support_vectors()[:, 0],
                    self.get_support_vectors()[:, 1], **square)


# fig, ax = plt.subplots()
# training_set = PointsDataset(10)
# X, y = training_set.get_X(), training_set.get_y()
# svm = SVM()
# svm.fit(X, y)
# svm.plot(X, y, ax=ax)
