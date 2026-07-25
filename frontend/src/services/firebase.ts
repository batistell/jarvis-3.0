import { initializeApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider, signInWithPopup, signOut, User } from 'firebase/auth';

// Configuração do Firebase para autenticação local
const firebaseConfig = {
  apiKey: "AIzaSyDummyKeyForLocalDevOnly12345",
  authDomain: "jarvis-1006b.firebaseapp.com",
  projectId: "jarvis-1006b",
  storageBucket: "jarvis-1006b.appspot.com",
  messagingSenderId: "123456789",
  appId: "1:123456789:web:dummyappid123"
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();

export const loginWithGoogle = async (): Promise<User | null> => {
  try {
    const result = await signInWithPopup(auth, googleProvider);
    return result.user;
  } catch (error) {
    console.warn('Erro ou cancelamento no Firebase Google Auth Popup:', error);
    return null;
  }
};

export const logoutFirebase = async (): Promise<void> => {
  await signOut(auth);
};
